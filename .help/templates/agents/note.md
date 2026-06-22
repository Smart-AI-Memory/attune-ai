---
type: note
name: agents-note
feature: agents
depth: note
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 4f67c2f70bbc6d8bdf391e3cbf1ac1e57c554913aa2b3b355f736347e5526634
status: generated
---

# Note: agents

## Context

The `agents` feature covers three concerns: release agents, state persistence, and recovery. It spans two source trees — `src/attune/agents/` and `src/attune/agent_factory/` — with framework adapters living under `src/attune/agent_factory/adapters/`.

## Framework adapters

Each supported framework has a matching adapter, agent, and workflow class:

| Framework | Adapter | Agent class | Workflow class |
|---|---|---|---|
| Microsoft AutoGen | `AutoGenAdapter` | `AutoGenAgent` | `AutoGenWorkflow` |
| deepset Haystack | `HaystackAdapter` | `HaystackAgent` | `HaystackWorkflow` |
| LangChain | `LangChainAdapter` | `LangChainAgent` | `LangChainWorkflow` |

Every adapter exposes `is_available()` to check whether the underlying framework is installed, and `create_agent()`, `create_workflow()`, and `create_tool()` to construct the framework-specific objects from shared `AgentConfig` and `WorkflowConfig` values.

## Lazy loading

Adapters are not imported at package load time. The top-level functions `get_autogen_adapter()`, `get_haystack_adapter()`, `get_langchain_adapter()`, and `get_langgraph_adapter()` each perform a lazy import, so only the frameworks you actually use contribute to import cost.

## Adapter and class composition

The adapter functions and the agent/workflow classes are designed to work together. Adapters produce agent and workflow instances; those instances expose `invoke()`, `stream()`, and `run()` methods that match the signatures expected by higher-level orchestration code. `wrap_wizard()` provides a shortcut when you want to treat an existing wizard as a `WizardAgent` without going through a full adapter.

## Resilience utilities

Several decorators in the feature support safe operation at runtime:

- `safe_agent_operation` wraps a method with logging and raises `AgentOperationError` on failure.
- `retry_on_failure` retries a failing operation up to `max_attempts` times with exponential backoff controlled by `delay` and `backoff`.
- `log_performance` logs any call that exceeds `threshold_seconds`.
- `validate_input` checks that required fields are present in dict input before the wrapped function runs.

State persistence and recovery are handled by `AgentStateStore`, `AgentStateRecord`, `AgentExecutionRecord`, and `AgentRecoveryManager`.

**Tags:** `agents`, `ai`, `release`
