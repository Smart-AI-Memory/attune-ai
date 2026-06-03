---
feature: ops-dashboard
depth: task
generated_at: 2026-06-03T02:40:23.545253+00:00
source_hash: 9d40fc6564f1c4cf6ab6839bf1b973ced7daa7230432b038f45b7e79011d84f4
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
   - `clear_cache()` in `src/attune/ops/anthropic_cost.py` — Empty the in-memory cache. Test-only convenience.
   - `load_admin_key()` in `src/attune/ops/anthropic_cost.py` — Return the admin API key, or ``None`` if unavailable.
   - `fetch_summary()` in `src/attune/ops/anthropic_cost.py` — Return the current cost summary or a categorized error.
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
- `clear_cache()` in `src/attune/ops/anthropic_cost.py`
- `load_admin_key()` in `src/attune/ops/anthropic_cost.py`
- `fetch_summary()` in `src/attune/ops/anthropic_cost.py`
- `add_subparser()` in `src/attune/ops/cli.py`
- `cmd_ops()` in `src/attune/ops/cli.py`
- `main()` in `src/attune/ops/cli.py`
