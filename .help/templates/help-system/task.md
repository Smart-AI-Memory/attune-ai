---
feature: help-system
depth: task
generated_at: 2026-04-06T16:05:32.003255+00:00
source_hash: caf95aed14eb4d6660007f9eacb673cd2c7f4d1f2ac8d5301599e9ffee1dad6f
status: generated
---

# Work with help system

Use help system when you need to progressive-depth help engine and template management.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/help/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what help system
   does today before making changes.
   The primary functions are:
   - `scan_project()` in `src/attune/help/bootstrap.py` — Scan a project and propose features.
   - `proposals_to_manifest()` in `src/attune/help/bootstrap.py` — Convert accepted proposals to a FeatureManifest.
   - `record_template_feedback()` in `src/attune/help/feedback.py` — Record user feedback on a template.
   - `get_template_confidence()` in `src/attune/help/feedback.py` — Get confidence score based on feedback.
   - `get_usage_weights()` in `src/attune/help/feedback.py` — Get template relevance weights from usage telemetry.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "help-system"`.

## Key files

- `src/attune/help/**`
- `packages/attune-help/src/attune_help/**`

## Common modifications

Functions you are most likely to modify:

- `scan_project()` in `src/attune/help/bootstrap.py`
- `proposals_to_manifest()` in `src/attune/help/bootstrap.py`
- `record_template_feedback()` in `src/attune/help/feedback.py`
- `get_template_confidence()` in `src/attune/help/feedback.py`
- `get_usage_weights()` in `src/attune/help/feedback.py`
- `search_by_tag()` in `src/attune/help/feedback.py`
- `list_tags()` in `src/attune/help/feedback.py`
- `get_workflow_help()` in `src/attune/help/feedback.py`
