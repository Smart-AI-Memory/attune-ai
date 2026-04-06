---
feature: doc-gen
depth: task
generated_at: 2026-04-06T04:28:21.456674+00:00
source_hash: 444c6caa95ffb8aba3f6ccaa58d9ed8e39b6778803e88559314abcc374802863
status: generated
---

# Work with doc gen

Use doc gen when you need to automatically generate documentation from source code, including API references, docstrings, and readme sections.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/workflows/document_gen/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what doc gen
   does today before making changes.
   The primary functions are:
   - `format_doc_gen_report()` in `src/attune/workflows/document_gen/report_formatter.py` — formats document generation output as a human-readable report

2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "doc-gen"`.

## Key files

- `src/attune/workflows/document_gen/**`

## Common modifications

Functions you are most likely to modify:

- `format_doc_gen_report()` in `src/attune/workflows/document_gen/report_formatter.py`
