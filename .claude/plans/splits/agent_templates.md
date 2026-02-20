# Split Plan: agent_templates.py

**File:** src/attune/orchestration/agent_templates.py
**Lines:** 753
**Created:** 2026-02-20

## Strategy

Convert single file into package directory with
`__init__.py` re-exports. All 18 importing files
continue working without changes.

## New Structure

```text
src/attune/orchestration/agent_templates/
  __init__.py          # Re-exports public API
  models.py            # AgentCapability, ResourceRequirements,
                       #   AgentTemplate (~160 lines)
  registry.py          # Registry functions: get_template,
                       #   get_all_templates, etc. (~100 lines)
  builtin_templates.py # 13 template definitions +
                       #   registration (~420 lines)
```

## Groupings

- **models.py**: Lines 29-186 (dataclasses + validation)
- **registry.py**: Lines 188-284, 710-753 (registry
  functions + public API)
- **builtin_templates.py**: Lines 287-707 (template
  definitions + registration calls)

## Import Impact

18 files import from this module. All use either:
- `from .agent_templates import X`
- `from attune.orchestration.agent_templates import X`

Both work identically with a package `__init__.py`.
Zero import changes needed.
