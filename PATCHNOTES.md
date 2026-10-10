# Patch Notes

## Unreleased
- Replace `Rack.rows`/`Rack.drawersPerRow` with `Rack.rowLayout` (per-row column counts, e.g.
  `[3, 2, 4]` for a jagged rack), and auto-generate a rack's drawers from that layout on
  create/edit (`MasterDataService.sync_drawers_for_rack`) — previously every drawer had to be
  added by hand after creating the rack. New drawers get sequential 1-pixel default ranges;
  growing a rack's layout later only adds the missing cells and never touches drawers the user
  has already edited. The rack form is now one comma-separated "row layout" text field instead
  of two number inputs, and saving a rack redirects straight to its drawers list.
- Replace `brain.yaml` (Codex-era governance) with `CLAUDE.md`; same documentation discipline,
  consolidated into one file.
- Fix README intro still describing the web UI as C#-based after the Python decision.
- Refactor `MasterDataService`: extract the repeated per-entity CRUD logic (list/get/create/
  update/delete for racks, drawers, parts, categories, manufacturers, tags, locations) into a
  single generic `CrudService`. Public API unchanged, all tests pass unmodified.
- Add import/export maintenance flows for master data (Milestone 2, now complete): `GET /export`
  downloads all master data as JSON; `GET /import` shows a paste-JSON form, `POST /import`
  validates and replaces only the entity types present in the payload — nothing is written if any
  part of the payload is invalid, and the error list shows every problem found, not just the
  first.
- Add pick-by-light logic (`backend/lighting.py`: `WledController`, `MockWledController`,
  `PickByLightService`) and a `/simulate` web view that highlights matching drawers green on a
  visual rack grid — usable and demoable with no physical ESP32/WLED hardware. Real hardware
  control (`HttpWledController`) is deferred until hardware exists; see `docs/decisions.md`.
- Add real WLED hardware control after all: new `wled_devices.json` master data entity
  (`id`, `host`, `hardwareConnected`) — one ESP32/WLED device can drive multiple racks — plus
  `HttpWledController` (WLED's real JSON HTTP API, built and tested against a fake HTTP server)
  and `DispatchingWledController`, which always updates the simulation and *additionally* calls
  real hardware only for devices with `hardwareConnected: true`. `/simulate` now shows a
  "🔌 live" / "(simulated)" badge per rack and reports (deduplicated) hardware errors without
  failing the page — one unreachable ESP32 doesn't block any other rack. See `docs/decisions.md`
  for why this was built before any physical device exists.
- Fix `HTTPServer` → `ThreadingHTTPServer`: the plain single-threaded server serialized a real
  browser's simultaneous connections, so one slow request blocked every other one (including
  unrelated button clicks) until it resolved — only surfaced interactively, not via the test
  suite, which never issues concurrent requests.
- Add real maintenance forms (create/edit/delete) for every master data entity: racks & their
  drawers together, parts with category/manufacturer/drawer dropdowns, a shared generic
  id+name form for categories/manufacturers/tags, and WLED devices. New regex-based route table
  in `backend/web.py` (replacing the old flat `if path == ...` chain) to support path parameters
  like `/racks/<id>/edit`. Also a real visual style pass (`backend/web_forms.py`'s `<style>`
  block) — consistent spacing, buttons, nav highlighting, form layout — replacing the handful of
  original skeleton CSS lines. Split the by-then 1270-line `web.py` into `web.py` (HTTP
  mechanics), `web_forms.py` (shared/general page rendering), and `web_forms_entities.py`
  (entity-specific rendering), per `CLAUDE.md`'s file-size guidance.
- Documented generic rack layouts, multi-ESP32 support, and UI scope.
- Document proposed JSON file structure for master and movement data.
- Add empty JSON data files for the proposed structure.
- Add JSON schema files describing the data formats.
- Add schema-to-data mapping file for quick lookup.
- Translate README data-structure and flow descriptions to English.
- Refined the roadmap to focus on remaining planning and software tasks.
- Removed planning bullets now covered by existing JSON definitions.
- Capture single-user, minimal user-flow requirements in the roadmap.
- Move clarified single-user flows and pick-by-light behavior into README.
- Add Python backend models and JSON storage for master data, plus unit tests.
- Decide to implement the web UI in Python for backend consistency.
- Add JSON stores and models for movement and index data files.
- Add backend service layer for CRUD access to JSON data stores.
- Add schema validation on JSON read/write with tests for invalid payloads.
- Add a minimal Python web UI skeleton with navigation and inventory view.
- Add part search and filtering service APIs with unit tests.
- Fix UI routing to accept trailing slashes on inventory paths.
- Normalize UI routes to handle index.html requests.
- Normalize UI routes to ignore duplicate slashes and index suffixes.
