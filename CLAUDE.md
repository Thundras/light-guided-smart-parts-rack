# Light-Guided Smart Parts Rack — Claude Code Configuration

Replaces the former `brain.yaml` (Codex-era governance file). Same underlying discipline, kept
because it worked well — just consolidated into one file instead of a separate rules/doc split.

## Stack

- Python 3, standard library only (no web framework — `http.server` directly in `backend/web.py`).
- JSON file storage under `data/`, no database. Schemas in `data/schema/`, validated on read/write.
- Tests: `pytest`, run via `python -m pytest tests/ -q`.

## Rules

- Do what has been asked; nothing more, nothing less.
- NEVER create files unless necessary — prefer editing existing files.
- ALWAYS read a file before editing it.
- Keep `backend/` modules focused: `models` (dataclasses), `storage` (JSON I/O), `services`
  (business logic), `schema` (validation), `web` (HTTP layer). Don't blur these boundaries.
- Prefer a shared generic implementation over repeating the same CRUD pattern per entity type —
  the services layer already does this (`CrudService`); extend it rather than copy-pasting a new
  block per entity.
- After code changes, run the test suite and add/update coverage for new behavior.

## Documentation

- `README.md` — project description, setup, usage. Keep in sync with actual stack decisions
  (e.g. if a planned tech choice changes, update the intro here too, not just `docs/decisions.md`).
- `ROADMAP.md` — milestones with outcome statements, dependencies, and `☐`/`☑` status markers.
  Mark tasks and milestones done as they complete; don't remove completed items.
- `PATCHNOTES.md` — user-visible changes, append-only.
- `docs/decisions.md` — architecture/dependency/schema decisions, with Context/Decision/Reasoning,
  append-only. Write one whenever a new library, schema strategy, or architecture pattern is
  chosen.
- No placeholders, no TODO/TBD text, no invented scope — if something isn't decided yet, say so
  plainly instead of filling the gap with fake content.

## Commits

Conventional commits (`feat`, `fix`, `refactor`, `test`, `docs`, `chore`, etc.), imperative mood,
subject ≤72 chars.
