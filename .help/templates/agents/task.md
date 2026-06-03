---
feature: agents
depth: task
generated_at: 2026-06-03T02:40:23.579468+00:00
source_hash: bf303cb6343cd2a2e035f09d7021c5950e3aeca3a8891276134183794ba30235
status: generated
---

# Work with agents

Use agents when you need to release agents, state persistence, and recovery.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/agents/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what agents
   does today before making changes.
   The primary functions are:
   - `get_langchain_adapter()` in `src/attune/agent_factory/adapters/__init__.py` — Get LangChain adapter (lazy import).
   - `get_langgraph_adapter()` in `src/attune/agent_factory/adapters/__init__.py` — Get LangGraph adapter (lazy import).
   - `get_autogen_adapter()` in `src/attune/agent_factory/adapters/__init__.py` — Get AutoGen adapter (lazy import).
   - `get_haystack_adapter()` in `src/attune/agent_factory/adapters/__init__.py` — Get Haystack adapter (lazy import).
   - `wrap_wizard()` in `src/attune/agent_factory/adapters/wizard_adapter.py` — Quick helper to wrap a wizard as an agent.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "agents"`.

## Key files

- `src/attune/agents/**`
- `src/attune/agent_factory/**`

## Common modifications

Functions you are most likely to modify:

- `get_langchain_adapter()` in `src/attune/agent_factory/adapters/__init__.py`
- `get_langgraph_adapter()` in `src/attune/agent_factory/adapters/__init__.py`
- `get_autogen_adapter()` in `src/attune/agent_factory/adapters/__init__.py`
- `get_haystack_adapter()` in `src/attune/agent_factory/adapters/__init__.py`
- `wrap_wizard()` in `src/attune/agent_factory/adapters/wizard_adapter.py`
- `safe_agent_operation()` in `src/attune/agent_factory/decorators.py`
- `retry_on_failure()` in `src/attune/agent_factory/decorators.py`
- `log_performance()` in `src/attune/agent_factory/decorators.py`
