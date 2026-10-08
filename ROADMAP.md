# Roadmap

## Milestone 1 — Planning and validation
**Outcome:** Backend data access is stable, validated, and covered by baseline tests.
**Milestone status:** ☑ Done
- ☑ Add backend service layer for CRUD access to JSON data stores.
- ☑ Add JSON schema validation on read/write with clear error reporting.
- ☑ Expand unit tests for validation failures and file-not-found scenarios.

## Milestone 2 — Core software foundation
**Outcome:** A usable UI shell is available with core data operations wired end-to-end.
**Depends on:** Milestone 1.
**Milestone status:** ☑ Done
- ☑ Establish a minimal web UI skeleton in Python (navigation and inventory views).
- ☑ Implement search and filtering APIs to support the UI.
- ☑ Add import/export maintenance flows for master data.

## Milestone 3 — Pick-by-light enablement
**Outcome:** Hardware control is integrated and configurable for multiple racks.
**Depends on:** Milestone 2.
**Milestone status:** ☐ In progress
- ☑ Build the pick-by-light logic and a WLED controller interface (`WledController`), with a
  `MockWledController` and a `/simulate` web view so the feature is usable and demoable without
  any physical ESP32/WLED hardware. Already routes per-rack to the correct `wled_instance`, so
  multiple simultaneous racks/targets work in the simulation.
- ☐ Add the real WLED control integration (`HttpWledController`, calling WLED's JSON HTTP API) —
  blocked on hardware actually existing.
- ☐ Verify multiple ESP32 targets against real hardware.

## Milestone 4 — Usability and scale
**Outcome:** System is optimized for larger datasets and richer metadata management.
**Depends on:** Milestone 2 and 3.
**Milestone status:** ☐ Not started
- ☐ Add performance checks for large inventories and monthly movement files.
- ☐ Extend metadata management (labels, calibration profiles, and LED presets).
