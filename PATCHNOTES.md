# Patch Notes

## Unreleased
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
