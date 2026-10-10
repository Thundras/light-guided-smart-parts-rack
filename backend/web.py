from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlparse

from .lighting import DispatchingWledController, HttpWledController, MockWledController, PickByLightService
from .schema import SchemaValidationError
from .services import ImportValidationError, MasterDataService, PartSearchCriteria, PartSearchService
from .storage import JsonMasterDataStore

# One simulated WLED controller per server process, so repeated /simulate requests (and the
# search form on that page) accumulate against the same simulated rack state instead of each
# request starting from a blank slate — matches what a real, persistent WLED device would do.
# Every /simulate request routes through DispatchingWledController, which always updates this
# (so the view stays meaningful even for racks whose ESP32 is actually live) and additionally
# calls _hardware_controller for any WledDevice with hardwareConnected=true.
_simulated_controller = MockWledController()
_hardware_controller = HttpWledController()


def reset_simulated_controller() -> None:
    """Replace the module-level simulated controller with a fresh one. Exists so tests can
    isolate /simulate's otherwise-process-wide state between test cases."""
    global _simulated_controller
    _simulated_controller = MockWledController()


def _render_layout(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>{title}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 2rem; }}
      header {{ margin-bottom: 1.5rem; }}
      nav a {{ margin-right: 1rem; }}
      table {{ border-collapse: collapse; width: 100%; }}
      th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
      .message {{ background: #f7f7f7; padding: 0.75rem; border-radius: 4px; }}
      .rack {{ margin-bottom: 2rem; }}
      .rack-grid {{ border-collapse: collapse; width: auto; }}
      .rack-grid td {{
        width: 4.5rem; height: 2.5rem; text-align: center; vertical-align: middle;
        font-size: 0.8rem; color: #fff; text-shadow: 0 0 2px #000;
      }}
      .rack-grid td.empty {{ background: transparent; border: none; }}
    </style>
  </head>
  <body>
    <header>
      <h1>Light-Guided Smart Parts Rack</h1>
      <nav>
        <a href="/">Home</a>
        <a href="/inventory">Inventory</a>
        <a href="/export">Export</a>
        <a href="/import">Import</a>
        <a href="/simulate">Simulate</a>
      </nav>
    </header>
    {body}
  </body>
</html>
"""


def _render_home() -> str:
    return _render_layout(
        "Home",
        "<p class=\"message\">Use the navigation to access inventory data.</p>",
    )


def _render_inventory(parts: Iterable[object], message: str | None = None) -> str:
    rows = "".join(
        f"<tr><td>{part.id}</td><td>{part.name}</td><td>{part.quantity}</td></tr>"
        for part in parts
    )
    if not rows:
        rows = "<tr><td colspan=\"3\">No parts available.</td></tr>"
    message_block = f"<p class=\"message\">{message}</p>" if message else ""
    body = f"""
    {message_block}
    <table>
      <thead>
        <tr>
          <th>Part ID</th>
          <th>Name</th>
          <th>Quantity</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
    """
    return _render_layout("Inventory", body)


def _render_import_form(message: str | None = None, errors: Iterable[str] = ()) -> str:
    errors = list(errors)
    message_block = f"<p class=\"message\">{_escape(message)}</p>" if message else ""
    errors_block = ""
    if errors:
        items = "".join(f"<li>{_escape(err)}</li>" for err in errors)
        errors_block = f'<div class="message"><strong>Import failed:</strong><ul>{items}</ul></div>'
    body = f"""
    {message_block}
    {errors_block}
    <p>Paste a JSON object in the shape produced by <a href="/export">Export</a>. Only the
    entity keys present in the payload are replaced; keys you leave out are left untouched.</p>
    <form method="post" action="/import">
      <textarea name="payload" rows="20" cols="80"
                placeholder='{{"racks": [...], "parts": [...]}}'></textarea><br/>
      <button type="submit">Import</button>
    </form>
    """
    return _render_layout("Import", body)


def _render_simulate(
    master: MasterDataService,
    controller: MockWledController,
    query: str,
    hardware_errors: Iterable[str] = (),
) -> str:
    """Pick-by-light simulation: runs a search against the query, highlights matching drawers
    green on the shared simulated controller, and renders each configured rack as a grid of
    drawers colored by the controller's current (post-search) state. Lets the pick-by-light
    behavior be seen and demoed without any real WLED/ESP32 hardware — and keeps showing the
    same view once a rack's ESP32 does go live (its drawers just also actually light up)."""
    racks = master.list_racks()
    drawers_by_rack: dict[str, list] = {rack.id: [] for rack in racks}
    for drawer in master.list_drawers():
        drawers_by_rack.setdefault(drawer.rack_id, []).append(drawer)
    connected_instances = {
        device.id for device in master.list_wled_devices() if device.hardware_connected
    }

    search_form = f"""
    <form method="get" action="/simulate">
      <input type="text" name="q" value="{_escape(query)}" placeholder="Search parts..." />
      <button type="submit">Highlight</button>
    </form>
    """

    hardware_errors = list(hardware_errors)
    errors_block = ""
    if hardware_errors:
        items = "".join(f"<li>{_escape(err)}</li>" for err in hardware_errors)
        errors_block = (
            f'<div class="message"><strong>Hardware unreachable (simulation still shown '
            f"below):</strong><ul>{items}</ul></div>"
        )

    if not racks:
        return _render_layout(
            "Simulate", search_form + errors_block + '<p class="message">No racks configured yet.</p>'
        )

    racks_html = []
    for rack in racks:
        by_position = {(d.row, d.col): d for d in drawers_by_rack.get(rack.id, [])}
        rows_html = []
        for row in range(rack.rows):
            cells = []
            for col in range(rack.drawers_per_row):
                drawer = by_position.get((row, col))
                if drawer is None:
                    cells.append('<td class="empty"></td>')
                    continue
                r, g, b = controller.color_for(rack.wled_instance, drawer.pixel_range)
                cells.append(
                    f'<td style="background: rgb({r},{g},{b})">{_escape(drawer.label)}</td>'
                )
            rows_html.append("<tr>" + "".join(cells) + "</tr>")
        live_badge = " 🔌 live" if rack.wled_instance in connected_instances else " (simulated)"
        racks_html.append(
            f'<div class="rack"><h2>{_escape(rack.name)}{live_badge}</h2>'
            f'<table class="rack-grid">{"".join(rows_html)}</table></div>'
        )

    return _render_layout("Simulate", search_form + errors_block + "".join(racks_html))


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class WebUIRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = _normalize_path(urlparse(self.path).path)
        if path == "/":
            self._send_html(_render_home())
            return
        if path == "/inventory":
            self._send_html(self._inventory_page())
            return
        if path == "/export":
            self._send_export()
            return
        if path == "/import":
            self._send_html(_render_import_form())
            return
        if path == "/simulate":
            self._send_html(self._simulate_page())
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_HEAD(self) -> None:
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.end_headers()

    def do_POST(self) -> None:
        path = _normalize_path(urlparse(self.path).path)
        if path == "/import":
            self._handle_import()
            return
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.end_headers()

    def _handle_import(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else ""
        raw_payload = parse_qs(body).get("payload", [""])[0]

        try:
            payload = json.loads(raw_payload) if raw_payload.strip() else {}
        except json.JSONDecodeError as exc:
            self._send_html(_render_import_form(errors=[f"Invalid JSON: {exc}"]))
            return

        if not isinstance(payload, dict):
            self._send_html(
                _render_import_form(errors=["Payload must be a JSON object keyed by entity type."])
            )
            return

        service = MasterDataService(JsonMasterDataStore(_repo_root()))
        try:
            service.import_all(payload)
        except ImportValidationError as exc:
            self._send_html(_render_import_form(errors=exc.errors))
            return

        imported = ", ".join(sorted(payload.keys())) or "nothing"
        self._send_html(_render_import_form(message=f"Import successful ({imported})."))

    def _send_export(self) -> None:
        service = MasterDataService(JsonMasterDataStore(_repo_root()))
        encoded = json.dumps(service.export_all(), indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="export.json"')
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _simulate_page(self) -> str:
        query_params = parse_qs(urlparse(self.path).query)
        query = query_params.get("q", [""])[0]

        store = JsonMasterDataStore(_repo_root())
        master = MasterDataService(store)
        # Always run highlight_parts, even with an empty query (-> no matches, not "match
        # everything" — PartSearchCriteria with no query would match all parts, which is right
        # for a real search but wrong as this page's empty/cleared state): it explicitly turns
        # every drawer off, not just the ones that matched last time, so clearing the search box
        # actually clears the simulated rack instead of leaving a stale highlight.
        matches = (
            PartSearchService(store).search_parts(PartSearchCriteria(query=query)) if query else []
        )

        # One error per unique WLED instance, not one per drawer on that instance — a rack with
        # 20 drawers on an offline ESP32 would otherwise show the same message 20 times.
        hardware_errors: dict[str, str] = {}
        dispatcher = DispatchingWledController(
            master,
            _simulated_controller,
            _hardware_controller,
            on_hardware_error=lambda instance, exc: hardware_errors.setdefault(instance, str(exc)),
        )
        PickByLightService(master, dispatcher).highlight_parts(matches)
        error_messages = [f"{instance}: {msg}" for instance, msg in hardware_errors.items()]
        return _render_simulate(master, _simulated_controller, query, error_messages)

    def _inventory_page(self) -> str:
        store = JsonMasterDataStore(_repo_root())
        try:
            parts = store.load_parts()
            return _render_inventory(parts)
        except FileNotFoundError:
            return _render_inventory(
                [],
                "Parts data file not found. Create data/master/parts.json to view inventory.",
            )
        except SchemaValidationError as exc:
            return _render_inventory([], f"Invalid parts data: {exc}")

    def _send_html(self, content: str) -> None:
        encoded = content.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def _repo_root() -> Path:
    # Overridable for tests, so the live HTTP server can be exercised end-to-end against a
    # scratch directory instead of this project's own data/ files.
    override = os.environ.get("SMART_RACK_REPO_ROOT")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[1]


def _normalize_path(path: str) -> str:
    path = path.strip()
    if not path:
        return "/"
    while "//" in path:
        path = path.replace("//", "/")
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    if path.endswith("/index.html"):
        path = path[: -len("/index.html")] or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return path


def run(host: str = "0.0.0.0", port: int = 8000) -> None:
    # ThreadingHTTPServer, not plain HTTPServer: a real browser opens several simultaneous
    # connections to the same page (parallel resource loads, favicon, keep-alive probing). A
    # single-threaded server serializes all of them, so any one slow/stuck connection blocks
    # every other request — including completely unrelated button clicks — until it resolves.
    # Confirmed this was actually happening (not just a theoretical concern) interactively.
    server = ThreadingHTTPServer((host, port), WebUIRequestHandler)
    print(f"Web UI running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
