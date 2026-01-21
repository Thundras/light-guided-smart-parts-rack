# Decisions

## 2026-01-21: Python web UI

### Context
The project needs a web UI for inventory tasks, and the current data layer work is in Python for JSON-based storage.

### Decision
Implement the web UI in Python to align the UI stack with the existing Python backend tooling.

### Reasoning
Using a single language simplifies development and testing workflows while keeping JSON handling consistent across the stack.
