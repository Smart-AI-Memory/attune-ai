# Split Plan: document_gen/workflow.py

**File:** src/attune/workflows/document_gen/workflow.py
**Lines:** 752
**Created:** 2026-02-20

## Strategy

Extract three stage methods into mixin classes, following
the existing mixin pattern in the package (api_reference,
chunked_generation, cost_management).

## New Files

- `outline_stage.py` — `OutlineStageMixin` with `_outline`
  and `_parse_outline_sections` (~190 lines)
- `write_stage.py` — `WriteStageMixin` with `_write`
  (~175 lines)
- `polish_stage.py` — `PolishStageMixin` with `_polish`
  (~230 lines)

## Modified Files

- `workflow.py` — Keeps `__init__`, `default_context`,
  `should_skip_stage`, `run_stage`. Inherits from new
  mixins. Reduced to ~160 lines.

## Import Impact

Only `__init__.py` in this package imports from
workflow.py. External code imports via the package.
No external import changes needed.
