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

## 2026-10-08: Simulated pick-by-light before any hardware exists

### Context
Milestone 3 (pick-by-light) needs WLED/ESP32 hardware to fully verify, and none exists yet (the
user explicitly wants the software built hardware-first, hardware added later). Building the
pick-by-light logic directly against a real `HttpWledController` would mean it can't be built,
tested, or demonstrated at all until a device is bought and flashed.

### Decision
Define a `WledController` interface (`backend/lighting.py`) with one real responsibility — set a
color on a given WLED instance's pixel range — and build `PickByLightService` against that
interface, not a concrete implementation. Ship a `MockWledController` that records calls instead
of making network requests, plus a `/simulate` web view that renders each rack as a drawer grid
colored from the mock's recorded state. `HttpWledController` (the real WLED JSON HTTP API client)
is deliberately not built yet.

### Reasoning
This mirrors the mock/real hardware-abstraction pattern already used successfully in the
`Freenove_Robot_New` project's `sal/` layer — hardware-dependent logic gets built and tested
against a software stand-in, with the real driver swapped in later as an isolated, additive
change once hardware exists, rather than letting the whole feature block on hardware availability.
The visual `/simulate` view (not just unit-test assertions on the mock's recorded state) was
specifically requested, so the feature is genuinely demoable — seeing the rack light up on screen
— rather than only verifiable by reading test code.

## 2026-10-08: Build real WLED hardware control before any hardware exists, switched per-ESP32

### Context
After the simulation-only decision above, the user asked to build the real `HttpWledController`
now too, rather than waiting for hardware — reasoning: they can configure a rack as soon as it's
physically built and then "flip a switch" to have it drive real hardware, without the software
blocking on hardware existing first. One ESP32 can drive multiple racks (and a rack's pixel
strip could, in principle, span devices in the future), so the natural place for a "go live"
switch is the WLED device itself, not the rack.

### Decision
- New master data entity `WledDevice` (`wled_devices.json`): `id`, `host` (network address),
  `hardwareConnected` (bool). `Rack.wled_instance` now refers to a `WledDevice.id`, not a raw
  host — the host is resolved through the device record.
- `HttpWledController` implements the real WLED JSON HTTP API (`POST /json/state` with a `seg`
  pixel-range + solid color), using only `urllib.request` (stdlib, no new dependency, consistent
  with the project's framework-free constraint). Not exercised against a real device yet, but
  fully built and tested against a fake local HTTP server.
- `DispatchingWledController` wraps a simulated and a hardware controller: every call **always**
  updates the simulated one (so `/simulate` stays meaningful regardless of hardware status — "the
  visualization runs in parallel", as requested), and **additionally** calls the hardware
  controller, but only for WLED instances whose device record has `hardwareConnected: true`. A
  hardware call that fails (`WledConnectionError`) is caught and reported through a callback
  rather than propagating, so one offline ESP32 doesn't block pick-by-light for every other rack
  in the same request. `/simulate` deduplicates these errors per device (not per drawer) before
  display.

### Reasoning
Switching per-WLED-device rather than per-rack or globally matches the actual physical
relationship the user described: one ESP32 can serve several racks, and new racks get configured
in software well before their hardware exists, so the toggle needs to live on the thing that
actually has a hardware/no-hardware state — the device — not on each rack that happens to use it.
Dual-writing to the simulated controller even when hardware is connected means `/simulate` never
needs special-casing for "is this rack live or not" beyond a status badge; it keeps reflecting the
logical pick-by-light state either way. Catching hardware errors at the dispatch boundary (rather
than, say, requiring the caller to handle them per-rack) keeps `PickByLightService` itself
unaware that hardware can fail at all — it only ever talks to the `WledController` interface.

## 2026-10-10: Maintenance UI — route table, module split, and the 500-line guideline

### Context
The UI had no way to create/edit/delete a rack, drawer, part, or WLED device except hand-editing
JSON and pasting it into `/import` — not usable day to day. Building real forms for 7 entity
types (`Location` excluded — unused, see the entry two above) meant going from 8 flat, static
routes to roughly 30 with path parameters (`/racks/<id>/edit`), and `backend/web.py` grew past
1270 lines in the process.

### Decision
- **Regex route table** instead of the flat `if path == "/foo":` chain: a module-level list of
  `(method, compiled_pattern, handler_name)` tuples, checked in order, with path segments captured
  via named groups (`?P<rack_id>`) and passed as kwargs to the handler method.
- **Module split**: `backend/web.py` keeps HTTP mechanics only (routing, request/response
  handling, the `WebUIRequestHandler` class). Page rendering moved out to `backend/web_forms.py`
  (shared/general: layout, nav, home, import, simulate, error/confirm-delete helpers) and
  `backend/web_forms_entities.py` (WLED devices, the id+name lookups, racks/drawers, parts) —
  pure functions, no HTTP/socket code, easy to read and test in isolation from request handling.
- **Shared generic form for categories/manufacturers/tags**: all three are structurally identical
  (`{id, name}`), so one `_LookupSpec`-parameterized route set and render pair covers all three
  instead of three near-identical copies — same reasoning as the earlier `CrudService` extraction.
- **`web.py` (723 lines) and `services.py` (589 lines) stay over `CLAUDE.md`'s 500-line
  guideline, deliberately.** Both are one cohesive class each (`WebUIRequestHandler`,
  `MasterDataService`) — splitting further would mean fragmenting a single class's methods across
  multiple files rather than separating genuinely different concerns, which is worse for
  readability than one longer file. The guideline's purpose (keep related code easy to find and
  reason about) is better served by two large-but-coherent files here than by an arbitrary split.

### Reasoning
The route table change was forced by path parameters, not a style preference — a flat chain
cannot match `/racks/<id>/edit` without the same regex machinery anyway, so formalizing it as a
small table is the straightforward solution, not an added abstraction. The module split follows
the same "split once size is visible, not up front" approach as the rest of this project: it
wasn't planned as three files from the start, only once the single-file version became genuinely
hard to navigate. The two remaining oversized files were a deliberate stopping point: both are
single classes where the 500-line guideline and "one cohesive unit per file" pull in opposite
directions, and the project's own existing practice (e.g. `MasterDataService` not being split
entity-by-entity) already favors the latter.
