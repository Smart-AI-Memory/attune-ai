---
feature: workflows
depth: task
generated_at: 2026-04-06T03:31:49.015202+00:00
source_hash: 0d8b9057c8f6004f5eebcc6a44723afdac2c83eff80a405599ad678761baf5a3
status: generated
---

# Work with workflows

Use workflows when you need to execute multi-model AI pipelines for specialized tasks like bug prediction, batch processing, or converting Agent SDK outputs.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/workflows/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what workflows
   does today before making changes.
   The primary functions are:
   - `discover_workflows()` in `src/attune/workflows/__init__.py` — Discover workflows via entry points and config.
   - `refresh_workflow_registry()` in `src/attune/workflows/__init__.py` — Refresh the global WORKFLOW_REGISTRY by re-discovering all workflows.
   - `get_opt_in_workflows()` in `src/attune/workflows/__init__.py` — Get the list of opt-in workflows that require explicit enabling.
   - `get_workflow()` in `src/attune/workflows/__init__.py` — Get a workflow class by name, routing to SDK variant automatically.
   - `list_workflows()` in `src/attune/workflows/__init__.py` — List available workflows with descriptions.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "workflows"`.

## Key files

- `src/attune/workflows/**`

## Common modifications

Functions you are most likely to modify:

- `discover_workflows()` in `src/attune/workflows/__init__.py`
- `refresh_workflow_registry()` in `src/attune/workflows/__init__.py`
- `get_opt_in_workflows()` in `src/attune/workflows/__init__.py`
- `get_workflow()` in `src/attune/workflows/__init__.py`
- `list_workflows()` in `src/attune/workflows/__init__.py`
- `collect_agent_output()` in `src/attune/workflows/agent_sdk_adapter.py`
- `build_result_text()` in `src/attune/workflows/agent_sdk_adapter.py`
- `get_max_budget_usd()` in `src/attune/workflows/agent_sdk_adapter.py`
