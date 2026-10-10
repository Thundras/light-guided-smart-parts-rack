"""Entity-specific HTML rendering for the maintenance UI (WLED devices, the id+name lookups —
categories/manufacturers/tags, racks & drawers, parts). Split out of web_forms.py, which keeps
the shared/general pages (layout, home, import, simulate)."""

from __future__ import annotations

from typing import Iterable, NamedTuple

from .models import Category, Drawer, Manufacturer, Part, Rack, Tag, WledDevice
from .web_forms import _escape, _render_errors, _render_layout

# --- WLED devices ----------------------------------------------------------------------------


def _render_wled_devices_list(devices: Iterable[WledDevice]) -> str:
    rows = "".join(
        f"<tr><td>{_escape(d.id)}</td><td>{_escape(d.host)}</td>"
        f"<td>{'🔌 connected' if d.hardware_connected else 'simulated'}</td>"
        f'<td class="row-actions"><a href="/wled-devices/{d.id}/edit">Edit</a>'
        f'<a href="/wled-devices/{d.id}/delete">Delete</a></td></tr>'
        for d in devices
    )
    if not rows:
        rows = '<tr><td colspan="4">No WLED devices yet.</td></tr>'
    body = f"""
    <div class="actions"><a href="/wled-devices/new" class="btn">+ New WLED Device</a></div>
    <table>
      <thead><tr><th>ID</th><th>Host</th><th>Status</th><th></th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    """
    return _render_layout("WLED Devices", body)


def _render_wled_device_form(device: WledDevice | None = None, errors: Iterable[str] = ()) -> str:
    is_edit = device is not None
    action = f"/wled-devices/{device.id}/edit" if is_edit else "/wled-devices/new"
    id_field = (
        f'<input type="text" name="id" value="{_escape(device.id)}" readonly />'
        if is_edit
        else '<input type="text" name="id" required />'
    )
    checked = "checked" if (device and device.hardware_connected) else ""
    body = f"""
    {_render_errors(errors)}
    <form class="stacked" method="post" action="{action}">
      <label>ID</label>
      {id_field}
      <label>Host (network address)</label>
      <input type="text" name="host" value="{_escape(device.host) if device else ''}" required />
      <div class="checkbox">
        <input type="checkbox" name="hardwareConnected" id="hardwareConnected" {checked} />
        <label for="hardwareConnected">Hardware connected (drive real WLED, not just simulate)</label>
      </div>
      <div class="form-actions">
        <button type="submit" class="btn">{"Save" if is_edit else "Create"}</button>
        <a href="/wled-devices" class="btn secondary">Cancel</a>
      </div>
    </form>
    """
    return _render_layout("WLED Devices", body)


# --- simple id+name lookups (categories, manufacturers, tags) --------------------------------


class _LookupSpec(NamedTuple):
    label: str
    plural_label: str
    url_prefix: str
    model: type
    list_fn: str
    get_fn: str
    create_fn: str
    update_fn: str
    delete_fn: str


_LOOKUP_SPECS: dict[str, _LookupSpec] = {
    "categories": _LookupSpec(
        "Category", "Categories", "/categories", Category,
        "list_categories", "get_category", "create_category", "update_category", "delete_category",
    ),
    "manufacturers": _LookupSpec(
        "Manufacturer", "Manufacturers", "/manufacturers", Manufacturer,
        "list_manufacturers", "get_manufacturer", "create_manufacturer", "update_manufacturer",
        "delete_manufacturer",
    ),
    "tags": _LookupSpec(
        "Tag", "Tags", "/tags", Tag,
        "list_tags", "get_tag", "create_tag", "update_tag", "delete_tag",
    ),
}


def _render_lookup_list(spec: _LookupSpec, items: Iterable) -> str:
    rows = "".join(
        f"<tr><td>{_escape(item.id)}</td><td>{_escape(item.name)}</td>"
        f'<td class="row-actions"><a href="{spec.url_prefix}/{item.id}/edit">Edit</a>'
        f'<a href="{spec.url_prefix}/{item.id}/delete">Delete</a></td></tr>'
        for item in items
    )
    if not rows:
        rows = f'<tr><td colspan="3">No {spec.plural_label.lower()} yet.</td></tr>'
    body = f"""
    <div class="actions"><a href="{spec.url_prefix}/new" class="btn">+ New {spec.label}</a></div>
    <table><thead><tr><th>ID</th><th>Name</th><th></th></tr></thead><tbody>{rows}</tbody></table>
    """
    return _render_layout(spec.plural_label, body)


def _render_lookup_form(spec: _LookupSpec, item=None, errors: Iterable[str] = ()) -> str:
    is_edit = item is not None
    action = f"{spec.url_prefix}/{item.id}/edit" if is_edit else f"{spec.url_prefix}/new"
    id_field = (
        f'<input type="text" name="id" value="{_escape(item.id)}" readonly />'
        if is_edit
        else '<input type="text" name="id" required />'
    )
    body = f"""
    {_render_errors(errors)}
    <form class="stacked" method="post" action="{action}">
      <label>ID</label>
      {id_field}
      <label>Name</label>
      <input type="text" name="name" value="{_escape(item.name) if item else ''}" required />
      <div class="form-actions">
        <button type="submit" class="btn">{"Save" if is_edit else "Create"}</button>
        <a href="{spec.url_prefix}" class="btn secondary">Cancel</a>
      </div>
    </form>
    """
    # nav highlighting matches on the plural nav label, not the singular form title
    return _render_layout(spec.plural_label, body)


# --- racks & drawers ---------------------------------------------------------------------------


def _render_racks_list(racks: Iterable[Rack]) -> str:
    rows = "".join(
        f"<tr><td>{_escape(r.id)}</td><td>{_escape(r.name)}</td>"
        f"<td>{_escape(r.wled_instance)}</td><td>{r.rows}×{r.drawers_per_row}</td>"
        f'<td class="row-actions"><a href="/racks/{r.id}/drawers">Drawers</a>'
        f'<a href="/racks/{r.id}/edit">Edit</a><a href="/racks/{r.id}/delete">Delete</a></td></tr>'
        for r in racks
    )
    if not rows:
        rows = '<tr><td colspan="5">No racks yet.</td></tr>'
    body = f"""
    <div class="actions"><a href="/racks/new" class="btn">+ New Rack</a></div>
    <table>
      <thead><tr><th>ID</th><th>Name</th><th>WLED Device</th><th>Layout</th><th></th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    """
    return _render_layout("Racks", body)


def _render_rack_form(
    devices: Iterable[WledDevice], rack: Rack | None = None, errors: Iterable[str] = ()
) -> str:
    devices = list(devices)
    is_edit = rack is not None
    action = f"/racks/{rack.id}/edit" if is_edit else "/racks/new"
    id_field = (
        f'<input type="text" name="id" value="{_escape(rack.id)}" readonly />'
        if is_edit
        else '<input type="text" name="id" required />'
    )
    if devices:
        options = "".join(
            f'<option value="{_escape(d.id)}"'
            f'{" selected" if rack and rack.wled_instance == d.id else ""}>'
            f"{_escape(d.id)} ({_escape(d.host)})</option>"
            for d in devices
        )
        wled_field = f'<select name="wledInstance" required>{options}</select>'
    else:
        wled_field = (
            '<p class="message">No WLED devices yet — '
            '<a href="/wled-devices/new">add one first</a>.</p>'
        )
    body = f"""
    {_render_errors(errors)}
    <form class="stacked" method="post" action="{action}">
      <label>ID</label>
      {id_field}
      <label>Name</label>
      <input type="text" name="name" value="{_escape(rack.name) if rack else ''}" required />
      <label>WLED Device</label>
      {wled_field}
      <label>Rows</label>
      <input type="number" name="rows" min="1" value="{rack.rows if rack else 1}" required />
      <label>Drawers per row</label>
      <input type="number" name="drawersPerRow" min="1"
             value="{rack.drawers_per_row if rack else 1}" required />
      <div class="form-actions">
        <button type="submit" class="btn">{"Save" if is_edit else "Create"}</button>
        <a href="/racks" class="btn secondary">Cancel</a>
      </div>
    </form>
    """
    return _render_layout("Racks", body)


def _render_drawers_list(rack: Rack, drawers: Iterable[Drawer]) -> str:
    rows = "".join(
        f"<tr><td>{_escape(d.id)}</td><td>{d.row}</td><td>{d.col}</td>"
        f"<td>{_escape(d.label)}</td>"
        f"<td>{d.pixel_range.start}–{d.pixel_range.start + d.pixel_range.count}</td>"
        f'<td class="row-actions"><a href="/drawers/{d.id}/edit">Edit</a>'
        f'<a href="/drawers/{d.id}/delete">Delete</a></td></tr>'
        for d in drawers
    )
    if not rows:
        rows = '<tr><td colspan="6">No drawers yet.</td></tr>'
    body = f"""
    <p><a href="/racks">&larr; All racks</a></p>
    <h2>{_escape(rack.name)} — Drawers</h2>
    <div class="actions"><a href="/drawers/new?rack_id={rack.id}" class="btn">+ New Drawer</a></div>
    <table>
      <thead><tr><th>ID</th><th>Row</th><th>Col</th><th>Label</th><th>Pixels</th><th></th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    """
    return _render_layout("Racks", body)


def _render_drawer_form(rack: Rack, drawer: Drawer | None = None, errors: Iterable[str] = ()) -> str:
    is_edit = drawer is not None
    action = f"/drawers/{drawer.id}/edit" if is_edit else "/drawers/new"
    id_field = (
        f'<input type="text" name="id" value="{_escape(drawer.id)}" readonly />'
        if is_edit
        else '<input type="text" name="id" required />'
    )
    body = f"""
    {_render_errors(errors)}
    <p class="message">Rack: <strong>{_escape(rack.name)}</strong></p>
    <form class="stacked" method="post" action="{action}">
      <input type="hidden" name="rackId" value="{_escape(rack.id)}" />
      <label>ID</label>
      {id_field}
      <label>Row</label>
      <input type="number" name="row" min="0" value="{drawer.row if drawer else 0}" required />
      <label>Column</label>
      <input type="number" name="col" min="0" value="{drawer.col if drawer else 0}" required />
      <label>Label</label>
      <input type="text" name="label" value="{_escape(drawer.label) if drawer else ''}" required />
      <label>Pixel range start</label>
      <input type="number" name="pixelStart" min="0"
             value="{drawer.pixel_range.start if drawer else 0}" required />
      <label>Pixel count</label>
      <input type="number" name="pixelCount" min="1"
             value="{drawer.pixel_range.count if drawer else 1}" required />
      <div class="form-actions">
        <button type="submit" class="btn">{"Save" if is_edit else "Create"}</button>
        <a href="/racks/{rack.id}/drawers" class="btn secondary">Cancel</a>
      </div>
    </form>
    """
    return _render_layout("Racks", body)


# --- parts ---------------------------------------------------------------------------------


def _render_parts_list(parts: Iterable[Part], message: str | None = None) -> str:
    message_block = f'<p class="message">{_escape(message)}</p>' if message else ""
    rows = "".join(
        f"<tr><td>{_escape(p.id)}</td><td>{_escape(p.name)}</td><td>{p.quantity}</td>"
        f'<td class="row-actions"><a href="/parts/{p.id}/edit">Edit</a>'
        f'<a href="/parts/{p.id}/delete">Delete</a></td></tr>'
        for p in parts
    )
    if not rows:
        rows = '<tr><td colspan="4">No parts yet.</td></tr>'
    body = f"""
    {message_block}
    <div class="actions"><a href="/parts/new" class="btn">+ New Part</a></div>
    <table>
      <thead><tr><th>ID</th><th>Name</th><th>Qty</th><th></th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    """
    return _render_layout("Parts", body)


def _render_part_form(
    categories: Iterable[Category],
    manufacturers: Iterable[Manufacturer],
    drawers_with_racks: Iterable[tuple[Drawer, Rack]],
    part: Part | None = None,
    errors: Iterable[str] = (),
) -> str:
    is_edit = part is not None
    action = f"/parts/{part.id}/edit" if is_edit else "/parts/new"
    id_field = (
        f'<input type="text" name="id" value="{_escape(part.id)}" readonly />'
        if is_edit
        else '<input type="text" name="id" required />'
    )

    category_options = "".join(
        f'<option value="{_escape(c.id)}"'
        f'{" selected" if part and part.category_id == c.id else ""}>{_escape(c.name)}</option>'
        for c in categories
    ) or '<option value="">No categories yet</option>'
    manufacturer_options = "".join(
        f'<option value="{_escape(m.id)}"'
        f'{" selected" if part and part.manufacturer_id == m.id else ""}>{_escape(m.name)}</option>'
        for m in manufacturers
    ) or '<option value="">No manufacturers yet</option>'
    drawer_options = "".join(
        f'<option value="{_escape(d.id)}"'
        f'{" selected" if part and part.drawer_id == d.id else ""}>'
        f"{_escape(r.name)} / {_escape(d.label)}</option>"
        for d, r in drawers_with_racks
    ) or '<option value="">No drawers yet</option>'
    tags_value = ", ".join(part.tags) if part else ""
    notes_value = part.notes if part and part.notes else ""

    body = f"""
    {_render_errors(errors)}
    <form class="stacked" method="post" action="{action}">
      <label>ID</label>
      {id_field}
      <label>Name</label>
      <input type="text" name="name" value="{_escape(part.name) if part else ''}" required />
      <label>Category</label>
      <select name="categoryId" required>{category_options}</select>
      <label>Manufacturer</label>
      <select name="manufacturerId" required>{manufacturer_options}</select>
      <label>Drawer</label>
      <select name="drawerId" required>{drawer_options}</select>
      <label>Quantity</label>
      <input type="number" name="quantity" min="0" value="{part.quantity if part else 0}" required />
      <label>Tags (comma-separated)</label>
      <input type="text" name="tags" value="{_escape(tags_value)}" />
      <label>Notes</label>
      <textarea name="notes" rows="3">{_escape(notes_value)}</textarea>
      <div class="form-actions">
        <button type="submit" class="btn">{"Save" if is_edit else "Create"}</button>
        <a href="/parts" class="btn secondary">Cancel</a>
      </div>
    </form>
    """
    return _render_layout("Parts", body)
