from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlparse

from .schema import SchemaValidationError
from .services import ImportValidationError, MasterDataService
from .storage import JsonMasterDataStore


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
    server = HTTPServer((host, port), WebUIRequestHandler)
    print(f"Web UI running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
