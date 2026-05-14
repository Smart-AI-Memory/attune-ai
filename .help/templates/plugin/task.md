---
feature: plugin
depth: task
generated_at: 2026-05-14T00:09:29.497930+00:00
source_hash: dad4ff4d931be93483178512f305df4124786c91adacb4cc3420e7e53450f49d
status: generated
---

# Work with plugin

Use plugin when you need to claude code plugin — skills, hooks, commands, and mcp config.

## Prerequisites

- Access to the project source code
- Familiarity with the files under plugin/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what plugin
   does today before making changes.
   The primary functions are:
   - `main()` in `plugin/hooks/_handoff_cli.py`
   - `build_resume_prompt()` in `plugin/hooks/_resume_prompt.py` — Render the user-facing resume prompt body.
   - `discover_specs()` in `plugin/hooks/_state.py` — Walk ``specs/`` directories under each root for in-flight specs.
   - `git_state()` in `plugin/hooks/_state.py` — Return branch, last commit, and uncommitted files for ``cwd``.
   - `session_sentinel_path()` in `plugin/hooks/_state.py` — Path to the once-per-session compact-warning sentinel.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "plugin"`.

## Key files

- `plugin/**`

## Common modifications

Functions you are most likely to modify:

- `main()` in `plugin/hooks/_handoff_cli.py`
- `build_resume_prompt()` in `plugin/hooks/_resume_prompt.py`
- `discover_specs()` in `plugin/hooks/_state.py`
- `git_state()` in `plugin/hooks/_state.py`
- `session_sentinel_path()` in `plugin/hooks/_state.py`
- `prune_stale_sentinels()` in `plugin/hooks/_state.py`
- `workspace_roots()` in `plugin/hooks/_state.py`
- `estimate_utilization()` in `plugin/hooks/_transcript_size.py`
