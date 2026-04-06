---
feature: security
depth: task
generated_at: 2026-04-06T03:32:26.888002+00:00
source_hash: cbec6dd3b97445fab938304744407004a55adcad528e799ba56896c354f5ad8e
status: generated
---

# Work with security

Use the security module when you need to validate paths and monitor LLM telemetry with an alert system.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/security/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what the security module
   does today before making changes.
   The primary functions are:
   - `alerts()` in `src/attune/monitoring/alerts_cli.py` — Manages alert commands for LLM telemetry monitoring.
   - `init()` in `src/attune/monitoring/alerts_cli.py` — Initializes an alert with interactive workflow or CLI flags.
   - `list_cmd()` in `src/attune/monitoring/alerts_cli.py` — Lists all configured alerts.
   - `delete()` in `src/attune/monitoring/alerts_cli.py` — Deletes an alert by ID.
   - `enable()` in `src/attune/monitoring/alerts_cli.py` — Enables an alert by ID.

2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "security"`.

## Key files

- `src/attune/security/**`
- `src/attune/monitoring/**`

## Common modifications

Functions you are most likely to modify:

- `alerts()` in `src/attune/monitoring/alerts_cli.py`
- `init()` in `src/attune/monitoring/alerts_cli.py`
- `list_cmd()` in `src/attune/monitoring/alerts_cli.py`
- `delete()` in `src/attune/monitoring/alerts_cli.py`
- `enable()` in `src/attune/monitoring/alerts_cli.py`
- `disable()` in `src/attune/monitoring/alerts_cli.py`
- `watch()` in `src/attune/monitoring/alerts_cli.py`
- `history()` in `src/attune/monitoring/alerts_cli.py`
