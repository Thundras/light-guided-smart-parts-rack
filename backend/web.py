from __future__ import annotations

import json
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Iterable, NamedTuple
from urllib.parse import parse_qs, urlparse

from .lighting import DispatchingWledController, HttpWledController, MockWledController, PickByLightService
from .models import Category, Drawer, Manufacturer, Part, PixelRange, Rack, Tag, WledDevice
from .schema import SchemaValidationError
from .services import ImportValidationError, MasterDataService, PartSearchCriteria, PartSearchService
from .storage import JsonMasterDataStore
from .web_forms import _render_confirm_delete, _render_home, _render_import_form, _render_simulate
from .web_forms_entities import (
    _LOOKUP_SPECS,
    _render_drawer_form,
    _render_drawers_list,
    _render_lookup_form,
    _render_lookup_list,
    _render_part_form,
    _render_parts_list,
    _render_rack_form,
    _render_racks_list,
    _render_wled_device_form,
    _render_wled_devices_list,
)

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


class Route(NamedTuple):
    method: str
    pattern: "re.Pattern[str]"
    handler: str  # WebUIRequestHandler method name; called as getattr(self, handler)(**groups)


# Regex-based route table instead of a flat if/elif chain: needed once routes take path
# parameters (/racks/<id>/edit) rather than being all-static strings. Checked in order; first
# match wins. Populated by _route() calls below, grouped by the entity each route manages.
ROUTES: list[Route] = []


def _route(method: str, pattern: str) -> Callable[[Callable], Callable]:
    compiled = re.compile(pattern)

    def register(func: Callable) -> Callable:
        ROUTES.append(Route(method, compiled, func.__name__))
        return func

    return register


class WebUIRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_HEAD(self) -> None:
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.end_headers()

    def do_POST(self) -> None:
        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        path = _normalize_path(urlparse(self.path).path)
        for route in ROUTES:
            if route.method != method:
                continue
            match = route.pattern.match(path)
            if match:
                getattr(self, route.handler)(**match.groupdict())
                return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    # --- shared request/response helpers -----------------------------------------------------

    def _read_form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else ""
        parsed = parse_qs(body)
        return {key: values[0] for key, values in parsed.items()}

    def _redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.end_headers()

    def _service(self) -> MasterDataService:
        return MasterDataService(JsonMasterDataStore(_repo_root()))

    @_route("GET", r"^/$")
    def _home(self) -> None:
        self._send_html(_render_home())

    @_route("GET", r"^/import$")
    def _import_form(self) -> None:
        self._send_html(_render_import_form())

    @_route("GET", r"^/export$")
    def _send_export(self) -> None:
        service = self._service()
        encoded = json.dumps(service.export_all(), indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="export.json"')
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    @_route("GET", r"^/simulate$")
    def _simulate_page_route(self) -> None:
        self._send_html(self._simulate_page())

    @_route("GET", r"^/inventory$")
    def _inventory_redirect(self) -> None:
        # /parts replaced the old read-only /inventory table; kept as a redirect so any
        # bookmarked/old link still lands somewhere useful instead of 404ing.
        self._redirect("/parts")

    @_route("POST", r"^/import$")
    def _handle_import(self) -> None:
        raw_payload = self._read_form().get("payload", "")

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

        service = self._service()
        try:
            service.import_all(payload)
        except ImportValidationError as exc:
            self._send_html(_render_import_form(errors=exc.errors))
            return

        imported = ", ".join(sorted(payload.keys())) or "nothing"
        self._send_html(_render_import_form(message=f"Import successful ({imported})."))

    # --- WLED devices ----------------------------------------------------------------------

    @_route("GET", r"^/wled-devices$")
    def _wled_devices_list(self) -> None:
        self._send_html(_render_wled_devices_list(self._service().list_wled_devices()))

    @_route("GET", r"^/wled-devices/new$")
    def _wled_device_new_form(self) -> None:
        self._send_html(_render_wled_device_form())

    @_route("POST", r"^/wled-devices/new$")
    def _wled_device_create(self) -> None:
        form = self._read_form()
        try:
            device = WledDevice(
                id=form.get("id", "").strip(),
                host=form.get("host", "").strip(),
                hardware_connected="hardwareConnected" in form,
            )
            if not device.id:
                raise ValueError("id is required")
            self._service().create_wled_device(device)
        except (ValueError, SchemaValidationError) as exc:
            self._send_html(_render_wled_device_form(errors=[str(exc)]))
            return
        self._redirect("/wled-devices")

    @_route("GET", r"^/wled-devices/(?P<device_id>[^/]+)/edit$")
    def _wled_device_edit_form(self, device_id: str) -> None:
        try:
            device = self._service().get_wled_device(device_id)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, "WLED device not found")
            return
        self._send_html(_render_wled_device_form(device))

    @_route("POST", r"^/wled-devices/(?P<device_id>[^/]+)/edit$")
    def _wled_device_update(self, device_id: str) -> None:
        form = self._read_form()
        device = WledDevice(
            id=device_id,
            host=form.get("host", "").strip(),
            hardware_connected="hardwareConnected" in form,
        )
        try:
            self._service().update_wled_device(device)
        except (ValueError, SchemaValidationError) as exc:
            self._send_html(_render_wled_device_form(device, errors=[str(exc)]))
            return
        self._redirect("/wled-devices")

    @_route("GET", r"^/wled-devices/(?P<device_id>[^/]+)/delete$")
    def _wled_device_delete_confirm(self, device_id: str) -> None:
        try:
            device = self._service().get_wled_device(device_id)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, "WLED device not found")
            return
        self._send_html(
            _render_confirm_delete(
                "Delete WLED Device",
                f"Delete WLED device '{device.id}' ({device.host})?",
                f"/wled-devices/{device.id}/delete",
                "/wled-devices",
            )
        )

    @_route("POST", r"^/wled-devices/(?P<device_id>[^/]+)/delete$")
    def _wled_device_delete(self, device_id: str) -> None:
        try:
            self._service().delete_wled_device(device_id)
        except ValueError:
            pass  # already gone; deleting a nonexistent record is a no-op for the user
        self._redirect("/wled-devices")

    # --- simple id+name lookups (categories, manufacturers, tags) --------------------------

    @_route("GET", r"^/(?P<kind>categories|manufacturers|tags)$")
    def _lookup_list(self, kind: str) -> None:
        spec = _LOOKUP_SPECS[kind]
        items = getattr(self._service(), spec.list_fn)()
        self._send_html(_render_lookup_list(spec, items))

    @_route("GET", r"^/(?P<kind>categories|manufacturers|tags)/new$")
    def _lookup_new_form(self, kind: str) -> None:
        self._send_html(_render_lookup_form(_LOOKUP_SPECS[kind]))

    @_route("POST", r"^/(?P<kind>categories|manufacturers|tags)/new$")
    def _lookup_create(self, kind: str) -> None:
        spec = _LOOKUP_SPECS[kind]
        form = self._read_form()
        try:
            item = spec.model(id=form.get("id", "").strip(), name=form.get("name", "").strip())
            if not item.id:
                raise ValueError("id is required")
            getattr(self._service(), spec.create_fn)(item)
        except (ValueError, SchemaValidationError) as exc:
            self._send_html(_render_lookup_form(spec, errors=[str(exc)]))
            return
        self._redirect(spec.url_prefix)

    @_route("GET", r"^/(?P<kind>categories|manufacturers|tags)/(?P<item_id>[^/]+)/edit$")
    def _lookup_edit_form(self, kind: str, item_id: str) -> None:
        spec = _LOOKUP_SPECS[kind]
        try:
            item = getattr(self._service(), spec.get_fn)(item_id)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, f"{spec.label} not found")
            return
        self._send_html(_render_lookup_form(spec, item))

    @_route("POST", r"^/(?P<kind>categories|manufacturers|tags)/(?P<item_id>[^/]+)/edit$")
    def _lookup_update(self, kind: str, item_id: str) -> None:
        spec = _LOOKUP_SPECS[kind]
        form = self._read_form()
        item = spec.model(id=item_id, name=form.get("name", "").strip())
        try:
            getattr(self._service(), spec.update_fn)(item)
        except (ValueError, SchemaValidationError) as exc:
            self._send_html(_render_lookup_form(spec, item, errors=[str(exc)]))
            return
        self._redirect(spec.url_prefix)

    @_route("GET", r"^/(?P<kind>categories|manufacturers|tags)/(?P<item_id>[^/]+)/delete$")
    def _lookup_delete_confirm(self, kind: str, item_id: str) -> None:
        spec = _LOOKUP_SPECS[kind]
        try:
            item = getattr(self._service(), spec.get_fn)(item_id)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, f"{spec.label} not found")
            return
        self._send_html(
            _render_confirm_delete(
                f"Delete {spec.label}",
                f"Delete {spec.label.lower()} '{item.name}' ({item.id})?",
                f"{spec.url_prefix}/{item.id}/delete",
                spec.url_prefix,
            )
        )

    @_route("POST", r"^/(?P<kind>categories|manufacturers|tags)/(?P<item_id>[^/]+)/delete$")
    def _lookup_delete(self, kind: str, item_id: str) -> None:
        spec = _LOOKUP_SPECS[kind]
        try:
            getattr(self._service(), spec.delete_fn)(item_id)
        except ValueError:
            pass
        self._redirect(spec.url_prefix)

    # --- racks & drawers ---------------------------------------------------------------------

    @_route("GET", r"^/racks$")
    def _racks_list(self) -> None:
        self._send_html(_render_racks_list(self._service().list_racks()))

    @_route("GET", r"^/racks/new$")
    def _rack_new_form(self) -> None:
        self._send_html(_render_rack_form(self._service().list_wled_devices()))

    @_route("POST", r"^/racks/new$")
    def _rack_create(self) -> None:
        form = self._read_form()
        service = self._service()
        try:
            rack = Rack(
                id=form.get("id", "").strip(),
                name=form.get("name", "").strip(),
                wled_instance=form.get("wledInstance", "").strip(),
                rows=int(form.get("rows", "0")),
                drawers_per_row=int(form.get("drawersPerRow", "0")),
            )
            if not rack.id:
                raise ValueError("id is required")
            service.create_rack(rack)
        except (ValueError, SchemaValidationError) as exc:
            self._send_html(_render_rack_form(service.list_wled_devices(), errors=[str(exc)]))
            return
        self._redirect("/racks")

    @_route("GET", r"^/racks/(?P<rack_id>[^/]+)/edit$")
    def _rack_edit_form(self, rack_id: str) -> None:
        service = self._service()
        try:
            rack = service.get_rack(rack_id)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, "Rack not found")
            return
        self._send_html(_render_rack_form(service.list_wled_devices(), rack))

    @_route("POST", r"^/racks/(?P<rack_id>[^/]+)/edit$")
    def _rack_update(self, rack_id: str) -> None:
        form = self._read_form()
        service = self._service()
        try:
            rack = Rack(
                id=rack_id,
                name=form.get("name", "").strip(),
                wled_instance=form.get("wledInstance", "").strip(),
                rows=int(form.get("rows", "0")),
                drawers_per_row=int(form.get("drawersPerRow", "0")),
            )
            service.update_rack(rack)
        except (ValueError, SchemaValidationError) as exc:
            self._send_html(_render_rack_form(service.list_wled_devices(), rack, errors=[str(exc)]))
            return
        self._redirect("/racks")

    @_route("GET", r"^/racks/(?P<rack_id>[^/]+)/delete$")
    def _rack_delete_confirm(self, rack_id: str) -> None:
        service = self._service()
        try:
            rack = service.get_rack(rack_id)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, "Rack not found")
            return
        drawer_count = sum(1 for d in service.list_drawers() if d.rack_id == rack_id)
        note = f" It has {drawer_count} drawer(s), which will be left dangling." if drawer_count else ""
        self._send_html(
            _render_confirm_delete(
                "Delete Rack",
                f"Delete rack '{rack.name}' ({rack.id})?{note}",
                f"/racks/{rack.id}/delete",
                "/racks",
            )
        )

    @_route("POST", r"^/racks/(?P<rack_id>[^/]+)/delete$")
    def _rack_delete(self, rack_id: str) -> None:
        try:
            self._service().delete_rack(rack_id)
        except ValueError:
            pass
        self._redirect("/racks")

    @_route("GET", r"^/racks/(?P<rack_id>[^/]+)/drawers$")
    def _rack_drawers_list(self, rack_id: str) -> None:
        service = self._service()
        try:
            rack = service.get_rack(rack_id)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, "Rack not found")
            return
        drawers = sorted(
            (d for d in service.list_drawers() if d.rack_id == rack_id),
            key=lambda d: (d.row, d.col),
        )
        self._send_html(_render_drawers_list(rack, drawers))

    @_route("GET", r"^/drawers/new$")
    def _drawer_new_form(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        rack_id = query.get("rack_id", [""])[0]
        try:
            rack = self._service().get_rack(rack_id)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, "Rack not found")
            return
        self._send_html(_render_drawer_form(rack))

    @_route("POST", r"^/drawers/new$")
    def _drawer_create(self) -> None:
        form = self._read_form()
        service = self._service()
        rack_id = form.get("rackId", "")
        try:
            rack = service.get_rack(rack_id)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, "Rack not found")
            return
        try:
            drawer = Drawer(
                id=form.get("id", "").strip(),
                rack_id=rack_id,
                row=int(form.get("row", "0")),
                col=int(form.get("col", "0")),
                label=form.get("label", "").strip(),
                pixel_range=PixelRange(
                    start=int(form.get("pixelStart", "0")),
                    count=int(form.get("pixelCount", "0")),
                ),
            )
            if not drawer.id:
                raise ValueError("id is required")
            service.create_drawer(drawer)
        except (ValueError, SchemaValidationError) as exc:
            self._send_html(_render_drawer_form(rack, errors=[str(exc)]))
            return
        self._redirect(f"/racks/{rack_id}/drawers")

    @_route("GET", r"^/drawers/(?P<drawer_id>[^/]+)/edit$")
    def _drawer_edit_form(self, drawer_id: str) -> None:
        service = self._service()
        try:
            drawer = service.get_drawer(drawer_id)
            rack = service.get_rack(drawer.rack_id)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, "Drawer not found")
            return
        self._send_html(_render_drawer_form(rack, drawer))

    @_route("POST", r"^/drawers/(?P<drawer_id>[^/]+)/edit$")
    def _drawer_update(self, drawer_id: str) -> None:
        form = self._read_form()
        service = self._service()
        rack_id = form.get("rackId", "")
        try:
            rack = service.get_rack(rack_id)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, "Rack not found")
            return
        try:
            drawer = Drawer(
                id=drawer_id,
                rack_id=rack_id,
                row=int(form.get("row", "0")),
                col=int(form.get("col", "0")),
                label=form.get("label", "").strip(),
                pixel_range=PixelRange(
                    start=int(form.get("pixelStart", "0")),
                    count=int(form.get("pixelCount", "0")),
                ),
            )
            service.update_drawer(drawer)
        except (ValueError, SchemaValidationError) as exc:
            self._send_html(_render_drawer_form(rack, drawer, errors=[str(exc)]))
            return
        self._redirect(f"/racks/{rack_id}/drawers")

    @_route("GET", r"^/drawers/(?P<drawer_id>[^/]+)/delete$")
    def _drawer_delete_confirm(self, drawer_id: str) -> None:
        service = self._service()
        try:
            drawer = service.get_drawer(drawer_id)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, "Drawer not found")
            return
        self._send_html(
            _render_confirm_delete(
                "Delete Drawer",
                f"Delete drawer '{drawer.label}' ({drawer.id})?",
                f"/drawers/{drawer.id}/delete",
                f"/racks/{drawer.rack_id}/drawers",
            )
        )

    @_route("POST", r"^/drawers/(?P<drawer_id>[^/]+)/delete$")
    def _drawer_delete(self, drawer_id: str) -> None:
        service = self._service()
        try:
            drawer = service.get_drawer(drawer_id)
        except ValueError:
            self._redirect("/racks")
            return
        rack_id = drawer.rack_id
        service.delete_drawer(drawer_id)
        self._redirect(f"/racks/{rack_id}/drawers")

    # --- parts ---------------------------------------------------------------------------------

    @_route("GET", r"^/parts$")
    def _parts_list(self) -> None:
        store = JsonMasterDataStore(_repo_root())
        try:
            parts = store.load_parts()
            self._send_html(_render_parts_list(parts))
        except FileNotFoundError:
            self._send_html(_render_parts_list([], "Parts data file not found."))
        except SchemaValidationError as exc:
            self._send_html(_render_parts_list([], f"Invalid parts data: {exc}"))

    @_route("GET", r"^/parts/new$")
    def _part_new_form(self) -> None:
        service = self._service()
        self._send_html(
            _render_part_form(
                service.list_categories(), service.list_manufacturers(), self._drawers_with_racks(service)
            )
        )

    @_route("POST", r"^/parts/new$")
    def _part_create(self) -> None:
        form = self._read_form()
        service = self._service()
        try:
            part = self._part_from_form(form, part_id=form.get("id", "").strip())
            if not part.id:
                raise ValueError("id is required")
            service.create_part(part)
        except (ValueError, SchemaValidationError) as exc:
            self._send_html(
                _render_part_form(
                    service.list_categories(),
                    service.list_manufacturers(),
                    self._drawers_with_racks(service),
                    errors=[str(exc)],
                )
            )
            return
        self._redirect("/parts")

    @_route("GET", r"^/parts/(?P<part_id>[^/]+)/edit$")
    def _part_edit_form(self, part_id: str) -> None:
        service = self._service()
        try:
            part = service.get_part(part_id)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, "Part not found")
            return
        self._send_html(
            _render_part_form(
                service.list_categories(),
                service.list_manufacturers(),
                self._drawers_with_racks(service),
                part,
            )
        )

    @_route("POST", r"^/parts/(?P<part_id>[^/]+)/edit$")
    def _part_update(self, part_id: str) -> None:
        form = self._read_form()
        service = self._service()
        try:
            part = self._part_from_form(form, part_id=part_id)
            service.update_part(part)
        except (ValueError, SchemaValidationError) as exc:
            self._send_html(
                _render_part_form(
                    service.list_categories(),
                    service.list_manufacturers(),
                    self._drawers_with_racks(service),
                    errors=[str(exc)],
                )
            )
            return
        self._redirect("/parts")

    @_route("GET", r"^/parts/(?P<part_id>[^/]+)/delete$")
    def _part_delete_confirm(self, part_id: str) -> None:
        service = self._service()
        try:
            part = service.get_part(part_id)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, "Part not found")
            return
        self._send_html(
            _render_confirm_delete(
                "Delete Part",
                f"Delete part '{part.name}' ({part.id})?",
                f"/parts/{part.id}/delete",
                "/parts",
            )
        )

    @_route("POST", r"^/parts/(?P<part_id>[^/]+)/delete$")
    def _part_delete(self, part_id: str) -> None:
        try:
            self._service().delete_part(part_id)
        except ValueError:
            pass
        self._redirect("/parts")

    def _part_from_form(self, form: dict[str, str], part_id: str) -> Part:
        tags = [t.strip() for t in form.get("tags", "").split(",") if t.strip()]
        notes = form.get("notes", "").strip() or None
        return Part(
            id=part_id,
            name=form.get("name", "").strip(),
            category_id=form.get("categoryId", "").strip(),
            manufacturer_id=form.get("manufacturerId", "").strip(),
            drawer_id=form.get("drawerId", "").strip(),
            tags=tags,
            quantity=int(form.get("quantity", "0")),
            notes=notes,
        )

    def _drawers_with_racks(self, service: MasterDataService) -> list[tuple[Drawer, Rack]]:
        racks_by_id = {r.id: r for r in service.list_racks()}
        return [
            (d, racks_by_id[d.rack_id])
            for d in service.list_drawers()
            if d.rack_id in racks_by_id
        ]

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
