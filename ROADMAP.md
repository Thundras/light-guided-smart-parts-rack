# Roadmap

## Planning
- Planning and validation tasks are tracked in the prioritized list below.

## Software foundation
- Foundation tasks (backend services, UI shell, WLED integration, multi-ESP32 support) are tracked in the prioritized list below.

## Usability and refinement
- Usability tasks (search, labeling, performance, import/export) are tracked in the prioritized list below.

## Open tasks (prioritized)
### P0 — Next steps
- Define a backend service layer around the JSON stores (CRUD for master, movement, and index data).
- Add JSON schema validation on read/write with clear error reporting.
- Establish a minimal web UI skeleton in Python (navigation and inventory views).
- Expand unit tests for validation failures and file-not-found scenarios.

### P1 — After P0
- Implement search and filtering APIs to support the UI.
- Add WLED control integration for pick-by-light workflows.
- Support multiple ESP32 targets with configurable rack mappings.
- Add import/export maintenance flows for master data.

### P2 — Later
- Add performance checks for large inventories and monthly movement files.
- Extend metadata management (labels, calibration profiles, and LED presets).
