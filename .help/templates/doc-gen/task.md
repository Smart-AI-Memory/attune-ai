---
feature: doc-gen
depth: task
generated_at: 2026-04-13T16:54:52.347797+00:00
source_hash: 67aadd029bbf773d9f478a4d4c750e25344dc6b0bd9e1edadbcf5151d83f3bff
status: generated
---

# Work with doc gen

Use doc gen when you need to generate documentation from source code through a multi-stage workflow that extracts API references, creates outlines, writes content, and polishes the final output.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/workflows/document_gen/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what doc gen
   does today before making changes.
   The primary functions are:
   - `format_doc_gen_report()` in `src/attune/workflows/document_gen/report_formatter.py` — Format document generation output as a human-readable report.
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
