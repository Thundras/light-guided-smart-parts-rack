# Light-Guided Smart Parts Rack

A smart small-parts storage rack for private use that uses pick-by-light
indicators to locate items quickly. The hardware uses WS2812B LEDs driven by
an ESP32 running WLED. The software includes a C#-based web UI for maintaining
inventory data and searching for parts.

## Core components
- **Lighting control:** WS2812B addressable LEDs via ESP32 with WLED.
- **Inventory management UI:** C# web UI for part maintenance and search.
- **Physical storage:** Modular rack with labeled compartments mapped to LEDs.

## Configuration needs
- Rack sizes can vary and use drawer-based storage.
- Layout must be generic with no fixed dimensions, counts, or arrangement.
- The number of rows and drawers per row must be configurable.
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
- `racks.json` – racks including the WLED/ESP32 instance
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
