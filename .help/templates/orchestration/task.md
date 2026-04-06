---
feature: orchestration
depth: task
generated_at: 2026-04-06T04:34:22.257240+00:00
source_hash: 17a454ede63282929b4218973c064c597cdd92171aa4073eb371476a859ea7b4
status: generated
---

# Work with orchestration

Use orchestration when you need to compose dynamic agent teams, implement complex workflow patterns, or create hierarchical delegation systems.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/orchestration/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what orchestration
   does today before making changes.
   The primary functions are:
   - `get_strategy()` in `src/attune/orchestration/_strategies/__init__.py` — Get strategy instance by name.
   - `register_strategy()` in `src/attune/orchestration/_strategies/__init__.py` — Register a strategy class by name.
   - `register_workflow()` in `src/attune/orchestration/_strategies/nesting.py` — Register a workflow for nested references.
   - `get_workflow()` in `src/attune/orchestration/_strategies/nesting.py` — Get a registered workflow by ID.
   - `get_template()` in `src/attune/orchestration/agent_templates/registry.py` — Retrieve template by ID.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "orchestration"`.

## Key files

- `src/attune/orchestration/**`
- `src/attune/coordination/**`

## Common modifications

Functions you are most likely to modify:

- `get_strategy()` in `src/attune/orchestration/_strategies/__init__.py`
- `register_strategy()` in `src/attune/orchestration/_strategies/__init__.py`
- `register_workflow()` in `src/attune/orchestration/_strategies/nesting.py`
- `get_workflow()` in `src/attune/orchestration/_strategies/nesting.py`
- `get_template()` in `src/attune/orchestration/agent_templates/registry.py`
- `get_all_templates()` in `src/attune/orchestration/agent_templates/registry.py`
- `get_templates_by_capability()` in `src/attune/orchestration/agent_templates/registry.py`
- `get_templates_by_tier()` in `src/attune/orchestration/agent_templates/registry.py`
