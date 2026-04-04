---
feature: orchestration
depth: task
generated_at: 2026-04-04T02:25:50.561185+00:00
source_hash: 17a454ede63282929b4218973c064c597cdd92171aa4073eb371476a859ea7b4
status: generated
---

# Working with Orchestration

## Overview

Common tasks for modifying or extending orchestration.

## Key Files

- `src/attune/orchestration/**`

- `src/attune/coordination/**`


## Common Modifications

Functions you may need to modify:

- `get_strategy()` in `src/attune/orchestration/_strategies/__init__.py`

- `register_strategy()` in `src/attune/orchestration/_strategies/__init__.py`

- `register_workflow()` in `src/attune/orchestration/_strategies/nesting.py`

- `get_workflow()` in `src/attune/orchestration/_strategies/nesting.py`

- `get_template()` in `src/attune/orchestration/agent_templates/registry.py`

- `get_all_templates()` in `src/attune/orchestration/agent_templates/registry.py`

- `get_templates_by_capability()` in `src/attune/orchestration/agent_templates/registry.py`

- `get_templates_by_tier()` in `src/attune/orchestration/agent_templates/registry.py`
