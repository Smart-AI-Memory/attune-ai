---
feature: refactor-plan
depth: task
generated_at: 2026-06-01T11:47:06.470639+00:00
source_hash: 6f279448091cd9ecd115ce65a7c82e22149b5ff442f0841471de09a630a0f293
status: generated
---

# Work with refactor plan

Use refactor plan when you need to detect code smells and generate a prioritized refactoring roadmap.

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
