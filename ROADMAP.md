# Roadmap

## Milestone 1 — Planning and validation
**Outcome:** Backend data access is stable, validated, and covered by baseline tests.
- Define a backend service layer around the JSON stores (CRUD for master, movement, and index data).
- Add JSON schema validation on read/write with clear error reporting.
- Expand unit tests for validation failures and file-not-found scenarios.

## Milestone 2 — Core software foundation
**Outcome:** A usable UI shell is available with core data operations wired end-to-end.
**Depends on:** Milestone 1.
- Establish a minimal web UI skeleton in Python (navigation and inventory views).
- Implement search and filtering APIs to support the UI.
- Add import/export maintenance flows for master data.

## Milestone 3 — Pick-by-light enablement
**Outcome:** Hardware control is integrated and configurable for multiple racks.
**Depends on:** Milestone 2.
- Add WLED control integration for pick-by-light workflows.
- Support multiple ESP32 targets with configurable rack mappings.

## Milestone 4 — Usability and scale
**Outcome:** System is optimized for larger datasets and richer metadata management.
**Depends on:** Milestone 2 and 3.
- Add performance checks for large inventories and monthly movement files.
- Extend metadata management (labels, calibration profiles, and LED presets).
