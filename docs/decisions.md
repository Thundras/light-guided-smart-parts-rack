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

## 2026-10-08: Import/export as paste-JSON form, full-replace per entity

### Context
Milestone 2's last remaining item was import/export maintenance flows for master data. Two design
choices needed to be made: how the user submits an import (file upload vs. something else), and
what "import" means semantically (merge new/changed records into existing data, vs. replace).

### Decision
- **Paste-JSON form, not file upload.** `GET /import` renders a `<textarea>` the user pastes
  `GET /export`'s output into (optionally edited) and submits via a plain
  `application/x-www-form-urlencoded` POST. No multipart/file-upload handling.
- **Full replace per entity, not a merge.** `POST /import` takes a JSON object keyed by entity
  type (`{"racks": [...], "parts": [...]}`); each entity type present in the payload **replaces**
  that entity's entire JSON file. Entity types *not* present in the payload are left untouched.
- **All-or-nothing validation.** Every entity in the payload is parsed and schema-validated before
  anything is written; if any record anywhere is invalid, nothing is written, and the error list
  reports every problem found (not just the first), via a new `ImportValidationError` in
  `services.py`.

### Reasoning
The project's `http.server`-only stack (see the earlier Python-UI decision) has no built-in
multipart parser, and adding one just for this one form would be a new dependency or a chunk of
hand-rolled parsing for a single-user personal tool — not worth it. A paste-JSON textarea needs
only stdlib `urllib.parse.parse_qs`, matches the single-user "edit the export file, paste it back"
maintenance workflow this milestone was written for, and keeps the implementation inside the
project's existing no-framework constraint.

Full-replace-per-entity (rather than a create/update merge) was chosen because "import" here means
"this is now the source of truth for this entity type" — the natural mental model when you've just
edited an exported file — and avoids ambiguous merge-conflict semantics (what happens when an
imported record's id already exists with different field values?) that a merge approach would need
to define. Validating everything before writing anything, with a complete error list rather than
fail-fast on the first bad record, matches the "clear error reporting" outcome already stated for
Milestone 1's schema validation work and avoids partial, half-imported state.
