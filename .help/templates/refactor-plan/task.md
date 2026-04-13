---
feature: refactor-plan
depth: task
generated_at: 2026-04-13T16:55:54.448985+00:00
source_hash: 05ca199fb5b9d09ed7030f06c407e71de2e78a2433624c15a7beacf294de4d07
status: generated
---

# Work with refactor plan

Use refactor plan when you need to prioritize technical debt and generate a structured refactoring strategy for your codebase.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/workflows/refactor_plan.py

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what refactor plan
   does today before making changes.
   The primary functions are:
   - `format_refactor_plan_report()` in `src/attune/workflows/refactor_plan_report.py` — Format refactor plan output as a human-readable report.
   - `main()` in `src/attune/workflows/refactor_plan_report.py` — CLI entry point for refactor planning workflow.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "refactor-plan"`.

## Key files

- `src/attune/workflows/refactor_plan.py`
- `src/attune/workflows/refactor_plan_report.py`

## Common modifications

Functions you are most likely to modify:

- `format_refactor_plan_report()` in `src/attune/workflows/refactor_plan_report.py`
- `main()` in `src/attune/workflows/refactor_plan_report.py`
