# Light-Guided Smart Parts Rack

A smart small-parts storage rack for private use that uses pick-by-light
indicators to locate items quickly. The hardware uses WS2812B LEDs driven by
an ESP32 running WLED. The software includes a Python-based web UI for
maintaining inventory data and searching for parts (see
[`docs/decisions.md`](docs/decisions.md) for why Python was chosen over the
originally planned C#).

## Core components
- **Lighting control:** WS2812B addressable LEDs via ESP32 with WLED.
- **Inventory management UI:** Python web UI for part maintenance and search.
- **Physical storage:** Modular rack with labeled compartments mapped to LEDs.

## Configuration needs
- Rack sizes can vary and use drawer-based storage.
- Layout must be generic with no fixed dimensions, counts, or arrangement.
- Each rack's row layout (how many drawers per row, independently per row) must be
  configurable, since physical racks can be irregular/jagged.
- The number of LEDs per drawer must be configurable.
- Each rack must declare which ESP32/WLED instance it uses.
- Each drawer must declare which pixel range it maps to.

## Data storage
- Manage data without a database, potentially using JSON files.

### Proposed JSON data structure
```
data/
  master/            # master data
  movements/         # movement data
  indexes/           # optional search/lookup tables
  schema/            # JSON schemas for data formats
```

#### `data/master/` (master data)
- `wled_devices.json` – physical ESP32/WLED instances (`id`, `host`, `hardwareConnected`); one
  device can drive multiple racks
- `racks.json` – racks including which WLED/ESP32 instance (`wled_devices.json` id) they use
- `drawers.json` – drawers/slots including pixel ranges
- `parts.json` – parts/items
- `categories.json` – categories
- `manufacturers.json` – manufacturers
- `tags.json` – tags/keywords
- `locations.json` – optional location definitions

#### `data/movements/` (movement data)
- `stock_movements_YYYYMM.json` – monthly movement files
- `adjustments_YYYYMM.json` – inventory and correction entries
- `reservations.json` – reservations

#### `data/indexes/` (optional)
- `parts_by_tag.json`
- `parts_by_category.json`
- `parts_by_drawer.json`

#### `data/schema/` (JSON-Schemas)
- `master/` for master data schemas
- `movements/` for movement data schemas
- `indexes/` for index schemas
- `schema-map.json` maps data files to the matching schemas

## UI scope
- Search criteria: name, category, manufacturer, drawer, and tags.
- Maintenance: create, edit, delete, import/export, and notes/images.

## User flows (single-user, minimal)
- Add, edit, and search parts as the primary UI flows.
- Inventory actions: stocking, picking, and relocating.
- Pick-by-light behavior: all matching drawers light green, all others off.

## Backend data access (initial)
- Python JSON storage layer for master data, matching the documented file layout.
- Unit tests cover JSON load/save and optional fields for parts/drawers.

## UI technology decision
- The web UI will be implemented in Python rather than C# to keep the stack consistent with the JSON backend tooling.
- Movement and index JSON files are supported for load/save operations, matching the schema layout.

## Pick-by-light: simulated and real hardware side by side
Racks can be configured and used fully before any ESP32 exists. Each configured rack points at a
`wled_devices.json` entry (by id); that device's `hardwareConnected` flag is the per-ESP32 switch:
- `false` (default): pick-by-light for every rack on that device is simulation-only.
- `true`: pick-by-light *also* sends the real WLED JSON HTTP API call to that device's `host`, in
  addition to updating the simulation — so `/simulate` keeps showing the same view either way, and
  flipping one device's switch on doesn't require touching any rack/drawer configuration. If a
  connected device can't actually be reached, that one device's error is shown on the page but
  doesn't block pick-by-light for any other rack.

See [`docs/decisions.md`](docs/decisions.md) for why this is built hardware-first instead of
waiting for a physical device to exist.

## UI skeleton (Python)
Run the minimal web UI locally with:
```
python -m backend.web
```
- `http://localhost:8000` – home
- `http://localhost:8000/inventory` – inventory table view
- `http://localhost:8000/export` / `/import` – master data maintenance (see Export/Import nav links)
- `http://localhost:8000/simulate?q=<search>` – pick-by-light view (search box on the page itself)

`SMART_RACK_REPO_ROOT` overrides which directory's `data/` the server reads/writes — used by the
test suite to run the live server against a scratch directory instead of this project's own data.
