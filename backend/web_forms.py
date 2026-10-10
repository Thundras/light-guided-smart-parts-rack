"""Shared/general HTML rendering for the web UI — page layout, nav, home, import, simulate, and
the small error/confirm-delete helpers reused across every entity form. Entity-specific rendering
(WLED devices, lookups, racks/drawers, parts) lives in web_forms_entities.py, which imports the
helpers here. No HTTP/socket code, no data access beyond the model objects handed in — split out
of web.py once that file grew past a readable size."""

from __future__ import annotations

from typing import Iterable

from .services import MasterDataService


def _render_layout(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>{title}</title>
    <style>
      :root {{
        --ink: #1f2430; --muted: #6b7280; --border: #e2e5ea; --panel: #f7f8fa;
        --accent: #2f6fed; --accent-dark: #1d4fb8; --danger: #d64545; --danger-dark: #b33434;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        font-family: -apple-system, Segoe UI, Arial, sans-serif; margin: 0; color: var(--ink);
        background: #fff;
      }}
      header {{ padding: 1.25rem 2rem; border-bottom: 1px solid var(--border); }}
      header h1 {{ margin: 0 0 0.75rem; font-size: 1.4rem; }}
      main {{ padding: 1.5rem 2rem; max-width: 72rem; }}
      nav {{ display: flex; flex-wrap: wrap; gap: 0.25rem; }}
      nav a {{
        color: var(--muted); text-decoration: none; padding: 0.35rem 0.7rem; border-radius: 5px;
        font-size: 0.92rem;
      }}
      nav a:hover {{ background: var(--panel); color: var(--ink); }}
      nav a.current {{ background: var(--accent); color: #fff; }}
      h2 {{ font-size: 1.15rem; margin: 1.75rem 0 0.75rem; }}
      h2:first-child {{ margin-top: 0; }}
      table {{ border-collapse: collapse; width: 100%; margin-bottom: 1rem; }}
      th, td {{ border-bottom: 1px solid var(--border); padding: 0.55rem 0.6rem; text-align: left; }}
      th {{ color: var(--muted); font-weight: 600; font-size: 0.85rem; text-transform: uppercase; }}
      tr:hover td {{ background: var(--panel); }}
      .message {{ background: var(--panel); border: 1px solid var(--border); padding: 0.75rem 1rem;
        border-radius: 6px; margin-bottom: 1rem; }}
      .message.error {{ background: #fdecec; border-color: #f3b9b9; color: var(--danger-dark); }}
      .actions {{ margin: 1rem 0; }}
      .btn {{
        display: inline-block; padding: 0.5rem 1rem; border-radius: 6px; border: 1px solid var(--accent);
        background: var(--accent); color: #fff; text-decoration: none; font-size: 0.9rem; cursor: pointer;
      }}
      .btn:hover {{ background: var(--accent-dark); }}
      .btn.secondary {{ background: #fff; color: var(--ink); border-color: var(--border); }}
      .btn.secondary:hover {{ background: var(--panel); }}
      .btn.danger {{ background: var(--danger); border-color: var(--danger); }}
      .btn.danger:hover {{ background: var(--danger-dark); }}
      .row-actions a {{ margin-right: 0.75rem; font-size: 0.85rem; }}
      form.stacked {{ max-width: 32rem; }}
      form.stacked label {{ display: block; font-size: 0.85rem; color: var(--muted); margin: 0.9rem 0 0.3rem; }}
      form.stacked input[type=text], form.stacked input[type=number],
      form.stacked select, form.stacked textarea {{
        width: 100%; padding: 0.5rem 0.6rem; border: 1px solid var(--border); border-radius: 6px;
        font-size: 0.95rem; font-family: inherit;
      }}
      form.stacked .checkbox {{ display: flex; align-items: center; gap: 0.5rem; margin-top: 1rem; }}
      form.stacked .checkbox label {{ margin: 0; }}
      form.stacked .form-actions {{ margin-top: 1.25rem; display: flex; gap: 0.6rem; }}
      .rack {{ margin-bottom: 2rem; }}
      .rack-grid {{ border-collapse: collapse; width: auto; }}
      .rack-grid td {{
        width: 4.5rem; height: 2.5rem; text-align: center; vertical-align: middle;
        font-size: 0.8rem; color: #fff; text-shadow: 0 0 2px #000; border: 1px solid var(--border);
      }}
      .rack-grid td.empty {{ background: transparent; border: none; }}
    </style>
  </head>
  <body>
    <header>
      <h1>Light-Guided Smart Parts Rack</h1>
      <nav>
        {_render_nav(title)}
      </nav>
    </header>
    <main>
      {body}
    </main>
  </body>
</html>
"""


_NAV_ITEMS = [
    ("Home", "/"),
    ("Parts", "/parts"),
    ("Categories", "/categories"),
    ("Manufacturers", "/manufacturers"),
    ("Tags", "/tags"),
    ("Racks", "/racks"),
    ("WLED Devices", "/wled-devices"),
    ("Export", "/export"),
    ("Import", "/import"),
    ("Simulate", "/simulate"),
]


def _render_nav(current_title: str) -> str:
    links = []
    for label, href in _NAV_ITEMS:
        css_class = ' class="current"' if label == current_title else ""
        links.append(f'<a href="{href}"{css_class}>{label}</a>')
    return "".join(links)


def _render_home() -> str:
    return _render_layout(
        "Home",
        "<p class=\"message\">Use the navigation to access inventory data.</p>",
    )


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
    controller,
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


def _render_errors(errors: Iterable[str]) -> str:
    errors = list(errors)
    if not errors:
        return ""
    items = "".join(f"<li>{_escape(err)}</li>" for err in errors)
    return f'<div class="message error"><strong>Please fix the following:</strong><ul>{items}</ul></div>'


def _render_confirm_delete(title: str, message: str, action: str, cancel_url: str) -> str:
    body = f"""
    <p class="message">{message}</p>
    <form method="post" action="{action}">
      <button type="submit" class="btn danger">Yes, delete</button>
      <a href="{cancel_url}" class="btn secondary">Cancel</a>
    </form>
    """
    return _render_layout(title, body)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
