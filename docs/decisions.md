# Decisions

## 2026-01-21: Python web UI

### Context
The project needs a web UI for inventory tasks, and the current data layer work is in Python for JSON-based storage.

### Decision
Implement the web UI in Python to align the UI stack with the existing Python backend tooling.

### Reasoning
Using a single language simplifies development and testing workflows while keeping JSON handling consistent across the stack.

## 2026-10-07: Generic CrudService for master data

### Context
`MasterDataService` repeated an identical list/get/create/update/delete pattern seven times, once
per entity type (racks, drawers, parts, categories, manufacturers, tags, locations) — differing
only in which store methods and id accessor were used.

### Decision
Extract the shared CRUD logic into a single generic `CrudService`, parameterized by load/save
functions and an id accessor. `MasterDataService` now composes one `CrudService` instance per
entity internally and keeps its existing flat method names (`list_racks`, `get_rack`, etc.) as
thin delegating wrappers, so the public API and existing tests are unaffected.

### Reasoning
The duplication was exact and already repeated seven times, so extracting it isn't premature
abstraction — it removes real duplication rather than guessing at future flexibility. Keeping the
flat per-entity methods on `MasterDataService` avoids an unrelated, broader API change (e.g.
`service.racks.create(...)`) that wasn't asked for and would have required updating callers/tests
beyond the scope of this cleanup. Also replaced `brain.yaml` with `CLAUDE.md` as the project's
governance file — same documentation rules (README/ROADMAP/PATCHNOTES/decisions split, no
placeholders, conventional commits), just consolidated into the tool this project is now
developed with.
