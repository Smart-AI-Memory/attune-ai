---
feature: agents
depth: task
generated_at: 2026-04-13T16:59:03.189226+00:00
source_hash: dee340db6e093bcd99d9c92c2873020de79933812d17cc3e14cb5331294ac993
status: generated
---

# Work with agents

Use agents when you need to prepare releases, assess code quality, or integrate with external AI agent frameworks like LangChain and AutoGen.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/agents/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what agents
   does today before making changes.
   The primary functions are:
   - `get_langchain_adapter()` in `src/attune/agent_factory/adapters/__init__.py` — Get LangChain adapter with lazy import for framework integration.
   - `get_langgraph_adapter()` in `src/attune/agent_factory/adapters/__init__.py` — Get LangGraph adapter with lazy import for workflow orchestration.
   - `get_autogen_adapter()` in `src/attune/agent_factory/adapters/__init__.py` — Get AutoGen adapter with lazy import for multi-agent conversations.
   - `get_haystack_adapter()` in `src/attune/agent_factory/adapters/__init__.py` — Get Haystack adapter with lazy import for document processing.
   - `wrap_wizard()` in `src/attune/agent_factory/adapters/wizard_adapter.py` — Convert a wizard into an agent interface for unified operation.
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
