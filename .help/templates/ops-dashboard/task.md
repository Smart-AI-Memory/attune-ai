---
feature: ops-dashboard
depth: task
generated_at: 2026-05-14T14:00:01.189332+00:00
source_hash: 395f221f9a789d9b8851955c90a8bcc4904e7c84a247bacee7036e1583b0ea42
status: generated
---

# Work with ops dashboard

Use ops dashboard when you need to local operations dashboard — workflow runner with per-feature scope picker, persisted run history, clickable workflow chaining, and live sse log streaming.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/ops/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what ops dashboard
   does today before making changes.
   The primary functions are:
   - `create_app()` in `src/attune/ops/__init__.py` — Lazy-import the FastAPI factory so importing attune doesn't pull FastAPI.
   - `build_config()` in `src/attune/ops/__init__.py` — Lazy import of the config builder.
   - `add_subparser()` in `src/attune/ops/cli.py` — Register the `ops` subparser on the main attune CLI parser.
   - `cmd_ops()` in `src/attune/ops/cli.py` — Run the dashboard server (blocking).
   - `main()` in `src/attune/ops/cli.py` — Standalone entry: ``python -m attune.ops``.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "ops-dashboard"`.

## Key files

- `src/attune/ops/**`

## Common modifications

Functions you are most likely to modify:

- `create_app()` in `src/attune/ops/__init__.py`
- `build_config()` in `src/attune/ops/__init__.py`
- `add_subparser()` in `src/attune/ops/cli.py`
- `cmd_ops()` in `src/attune/ops/cli.py`
- `main()` in `src/attune/ops/cli.py`
- `attune_home()` in `src/attune/ops/config.py`
- `build_config()` in `src/attune/ops/config.py`
- `list_features()` in `src/attune/ops/data.py`
