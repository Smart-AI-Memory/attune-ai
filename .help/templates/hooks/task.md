---
feature: hooks
depth: task
generated_at: 2026-05-31T14:15:05.556631+00:00
source_hash: 42b6f3d8928cb9d9f896c40c595715ed3473820bfdc5f12e14e2889aea7c4d0a
status: generated
---

# Work with hooks

Use hooks when you need to hook system — pre/post-tool events, webhooks, and hook executor.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/hooks/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what hooks
   does today before making changes.
   The primary functions are:
   - `run_evaluate_session()` in `src/attune/hooks/scripts/evaluate_session.py` — Evaluate a session for learning potential.
   - `get_learning_summary()` in `src/attune/hooks/scripts/evaluate_session.py` — Get learning summary for a user.
   - `apply_learned_patterns()` in `src/attune/hooks/scripts/evaluate_session.py` — Generate context injection from learned patterns.
   - `get_project_root()` in `src/attune/hooks/scripts/first_time_init.py` — Get the project root directory.
   - `is_initialized()` in `src/attune/hooks/scripts/first_time_init.py` — Check if Attune AI is initialized in the project.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "hooks"`.

## Key files

- `src/attune/hooks/**`

## Common modifications

Functions you are most likely to modify:

- `run_evaluate_session()` in `src/attune/hooks/scripts/evaluate_session.py`
- `get_learning_summary()` in `src/attune/hooks/scripts/evaluate_session.py`
- `apply_learned_patterns()` in `src/attune/hooks/scripts/evaluate_session.py`
- `get_project_root()` in `src/attune/hooks/scripts/first_time_init.py`
- `is_initialized()` in `src/attune/hooks/scripts/first_time_init.py`
- `get_never_ask_file()` in `src/attune/hooks/scripts/first_time_init.py`
- `should_skip_init()` in `src/attune/hooks/scripts/first_time_init.py`
- `mark_never_ask()` in `src/attune/hooks/scripts/first_time_init.py`
