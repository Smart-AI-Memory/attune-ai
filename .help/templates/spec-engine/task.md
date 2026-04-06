---
feature: spec-engine
depth: task
generated_at: 2026-04-06T04:35:50.879254+00:00
source_hash: 9a5e04c503c29d581c2787038d961b7e425b0163cece10376e6b23a94fbb5aa4
status: generated
---

# Work with spec engine

Use spec engine when you need to execute XML specs with per-task approval loops and state persistence for iterative development.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/spec/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what spec engine
   does today before making changes.
   The primary functions are:
   - `present_tasks()` in `src/attune/spec/presenter.py` — Format all tasks as a human-readable markdown table.
   - `present_task_detail()` in `src/attune/spec/presenter.py` — Format a single task with full details.
   - `present_task_result()` in `src/attune/spec/presenter.py` — Format a task's execution result with quality gate status.
   - `format_progress_bar()` in `src/attune/spec/presenter.py` — Visual progress indicator for task execution.
   - `get_pending_tasks()` in `src/attune/spec/runner.py` — Filter tasks to only those not yet completed.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "spec-engine"`.

## Key files

- `src/attune/spec/**`
- `src/attune/pipeline/**`

## Common modifications

Functions you are most likely to modify:

- `present_tasks()` in `src/attune/spec/presenter.py`
- `present_task_detail()` in `src/attune/spec/presenter.py`
- `present_task_result()` in `src/attune/spec/presenter.py`
- `format_progress_bar()` in `src/attune/spec/presenter.py`
- `get_pending_tasks()` in `src/attune/spec/runner.py`
- `execute_with_approval()` in `src/attune/spec/runner.py`
- `load_state()` in `src/attune/spec/state.py`
- `save_state()` in `src/attune/spec/state.py`
