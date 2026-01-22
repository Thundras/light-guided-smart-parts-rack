# Patch Notes

## Unreleased
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
