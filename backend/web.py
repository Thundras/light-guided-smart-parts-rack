from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from .schema import SchemaValidationError
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


class WebUIRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = _normalize_path(urlparse(self.path).path)
        if path == "/":
            self._send_html(_render_home())
            return
        if path == "/inventory":
            self._send_html(self._inventory_page())
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_HEAD(self) -> None:
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.end_headers()

    def do_POST(self) -> None:
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.end_headers()

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
