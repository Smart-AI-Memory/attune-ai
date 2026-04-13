---
feature: bug-predict
depth: task
generated_at: 2026-04-13T16:55:12.298881+00:00
source_hash: bdce26567d10cd4bcfc419ff9a7191f2baac8f5a8e219c06d9ae6c6e38f95653
status: generated
---

# Work with bug predict

Use bug predict when you need to identify potential bug locations in your codebase through pattern detection and complexity analysis.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/workflows/bug_predict.py

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what bug predict
   does today before making changes.
   The primary functions are:
   - `format_bug_predict_report()` in `src/attune/workflows/bug_predict_report.py` — Formats bug prediction output as a human-readable report.
   - `main()` in `src/attune/workflows/bug_predict_report.py` — Provides CLI entry point for the bug prediction workflow.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "bug-predict"`.

## Key files

- `src/attune/workflows/bug_predict.py`
- `src/attune/workflows/bug_predict_*.py`

## Common modifications

Functions you are most likely to modify:

- `format_bug_predict_report()` in `src/attune/workflows/bug_predict_report.py`
- `main()` in `src/attune/workflows/bug_predict_report.py`
