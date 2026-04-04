---
feature: agents
depth: task
generated_at: 2026-04-04T02:25:50.462538+00:00
source_hash: f4444f832b2067c6c0ece4cfebdca1ecf9eb7d5b16efcf3ba756c35f5da24167
status: generated
---

# Working with Agents

## Overview

Common tasks for modifying or extending agents.

## Key Files

- `src/attune/agents/**`

- `src/attune/agent_factory/**`


## Common Modifications

Functions you may need to modify:

- `get_langchain_adapter()` in `src/attune/agent_factory/adapters/__init__.py`

- `get_langgraph_adapter()` in `src/attune/agent_factory/adapters/__init__.py`

- `get_autogen_adapter()` in `src/attune/agent_factory/adapters/__init__.py`

- `get_haystack_adapter()` in `src/attune/agent_factory/adapters/__init__.py`

- `wrap_wizard()` in `src/attune/agent_factory/adapters/wizard_adapter.py`

- `safe_agent_operation()` in `src/attune/agent_factory/decorators.py`

- `retry_on_failure()` in `src/attune/agent_factory/decorators.py`

- `log_performance()` in `src/attune/agent_factory/decorators.py`
