# Roadmap

## Planning
- Define rack dimensions, compartment count, and LED-to-compartment mapping.
- Capture configuration rules for variable rack sizes and drawer-based layouts.
- Specify how rows, drawers per row, and LEDs per drawer are defined.
- Require rack entries to reference the target ESP32/WLED endpoint.
- Require drawer entries to define pixel position and pixel count.
- Specify the data model for parts, locations, and LED addresses.
- Document the user flows for adding, editing, and searching parts.

## Hardware bring-up
- Select power supply, wiring plan, and LED chain limits for WS2812B.
- Configure ESP32 with WLED and validate LED addressing scheme.
- Build a minimal prototype with a subset of compartments.

## Software foundation
- Implement the C# web UI shell and navigation for inventory tasks.
- Integrate WLED control endpoints for pick-by-light activation.
- Support multiple ESP32 targets across different racks.
- Persist inventory data without a database (e.g., JSON-backed storage).

## Usability and refinement
- Add search filters and quick-pick workflows.
- Improve labeling, calibration, and LED brightness profiles.
- Validate performance and reliability in day-to-day use.
- Expand maintenance flows for import/export and rich metadata.
