---
feature: workflows
depth: task
generated_at: 2026-04-04T02:25:50.273759+00:00
source_hash: 0d8b9057c8f6004f5eebcc6a44723afdac2c83eff80a405599ad678761baf5a3
status: generated
---

# Working with Workflows

## Overview

Common tasks for modifying or extending workflows.

## Key Files

- `src/attune/workflows/**`


## Common Modifications

Functions you may need to modify:

- `discover_workflows()` in `src/attune/workflows/__init__.py`

- `refresh_workflow_registry()` in `src/attune/workflows/__init__.py`

- `get_opt_in_workflows()` in `src/attune/workflows/__init__.py`

- `get_workflow()` in `src/attune/workflows/__init__.py`

- `list_workflows()` in `src/attune/workflows/__init__.py`

- `collect_agent_output()` in `src/attune/workflows/agent_sdk_adapter.py`

- `build_result_text()` in `src/attune/workflows/agent_sdk_adapter.py`

- `get_max_budget_usd()` in `src/attune/workflows/agent_sdk_adapter.py`
