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
  master/            # Stammdaten
  movements/         # Bewegungsdaten
  indexes/           # optionale Such-/Lookup-Tabellen
  schema/            # JSON-Schemas für die Datenformate
```

#### `data/master/` (Stammdaten)
- `racks.json` – Racks inkl. WLED/ESP32-Instanz
- `drawers.json` – Schubladen/Slots inkl. Pixelbereich
- `parts.json` – Teile/Artikel
- `categories.json` – Kategorien
- `manufacturers.json` – Hersteller
- `tags.json` – Tags/Schlagworte
- `locations.json` – optionale Standort-Definitionen

#### `data/movements/` (Bewegungsdaten)
- `stock_movements_YYYYMM.json` – monatliche Bewegungsdateien
- `adjustments_YYYYMM.json` – Inventur- und Korrekturbuchungen
- `reservations.json` – Reservierungen

#### `data/indexes/` (optional)
- `parts_by_tag.json`
- `parts_by_category.json`
- `parts_by_drawer.json`

#### `data/schema/` (JSON-Schemas)
- `master/` für Stammdaten-Schemas
- `movements/` für Bewegungsdaten-Schemas
- `indexes/` für Index-Schemas
- `schema-map.json` ordnet Daten-Dateien den passenden Schemas zu

## UI scope
- Search criteria: name, category, manufacturer, drawer, and tags.
- Maintenance: create, edit, delete, import/export, and notes/images.
