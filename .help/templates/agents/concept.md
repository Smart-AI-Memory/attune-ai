---
type: concept
name: agents-concept
feature: agents
depth: concept
generated_at: 2026-06-04T23:45:26.733581+00:00
source_hash: 1e0485a1d4d99146ba7b61c353f12a4e84f199551b1b95660a8148e047f01d2f
status: generated
---

# Agents

Attune's agent system is a framework-agnostic layer that lets you create, run, and recover AI agents regardless of whether the underlying runtime is AutoGen, Haystack, or LangChain.

## Mental model

Three concepts compose the agent system:

- **Adapters** translate between Attune's unified interface and a specific AI framework. Each adapter (for example, `AutoGenAdapter`, `HaystackAdapter`, `LangChainAdapter`) implements `is_available()`, `create_agent()`, `create_workflow()`, and `create_tool()`. You pick an adapter once; the rest of your code stays the same.
- **Agents** are the runtime units of work. Each agent wraps a framework-native object — for example, `AutoGenAgent` wraps an AutoGen `AssistantAgent` or `UserProxyAgent`, while `HaystackAgent` wraps a Haystack `Pipeline` or `Component`. Every agent exposes `invoke()` for a single response and `stream()` for incremental output.
- **Workflows** coordinate multiple agents. `AutoGenWorkflow` uses AutoGen's `GroupChat`; `HaystackWorkflow` uses a Haystack `Pipeline`; `LangChainWorkflow` uses a `SequentialChain` or custom routing. Every workflow exposes `run()` and `stream()`.

The result is a two-level hierarchy: an adapter produces agents and workflows; agents and workflows run your logic.

## Framework adapters

Each adapter is obtained through a lazy-import helper so that only the frameworks you actually use are loaded:

| Helper | Adapter class | Framework |
|---|---|---|
| `get_autogen_adapter()` | `AutoGenAdapter` | Microsoft AutoGen |
| `get_haystack_adapter()` | `HaystackAdapter` | deepset Haystack |
| `get_langchain_adapter()` | `LangChainAdapter` | LangChain |
| `get_langgraph_adapter()` | — | LangGraph |

Call `adapter.is_available()` before use; it returns `False` if the optional framework dependency is not installed, letting you degrade gracefully.

`HaystackAdapter` also exposes `create_document_store()`, which the other adapters do not — useful when building retrieval-augmented workflows.

## Release agents and built-in specializations

Beyond generic agents, the system ships purpose-built agents for release engineering:

- `ReleaseAgent`, `CodeQualityAgent`, `DocumentationAgent`, `SecurityAuditorAgent`, and `TestCoverageAgent` are concrete agent types covering common release-readiness concerns.
- `ReleasePrepTeam` and `ReleasePrepTeamWorkflow` coordinate those agents into a team that produces a `ReleaseReadinessReport`.

You can also wrap an existing wizard object as an agent with `wrap_wizard(wizard, name, model_tier)`, which returns a `WizardAgent` without requiring a full adapter setup.

## State persistence and recovery

The `AgentStateStore` records `AgentStateRecord` snapshots so that agent progress survives interruptions. `AgentExecutionRecord` tracks individual execution history. When a failure occurs, `AgentRecoveryManager` reads those records and resumes or retries the affected agent.

## Resilience decorators

Several decorators harden agent operations without changing their signatures:

| Decorator | What it does |
|---|---|
| `safe_agent_operation(operation_name)` | Catches exceptions, logs them, and raises `AgentOperationError` |
| `retry_on_failure(max_attempts, delay, backoff, exceptions)` | Retries with exponential backoff |
| `log_performance(threshold_seconds)` | Logs calls that exceed the threshold |
| `validate_input(required_fields)` | Raises `ValueError` if required dict keys are absent |
| `with_cost_tracking(operation_type)` | Records API cost for the decorated call |

Apply these to any `invoke()` or `run()` implementation to get consistent error handling and observability across frameworks.

## When this matters

You need the agent system when:

- You want to write agent logic once and switch AI frameworks without rewriting call sites.
- You need multi-agent coordination (use a `*Workflow` class and let the adapter wire the group chat or pipeline).
- You need agents to survive process restarts (`AgentStateStore` + `AgentRecoveryManager`).
- You want release-readiness checks automated across code quality, documentation, security, and test coverage (`ReleasePrepTeam`).
