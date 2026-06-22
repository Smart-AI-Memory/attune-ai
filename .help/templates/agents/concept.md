---
type: concept
name: agents-concept
feature: agents
depth: concept
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 4f67c2f70bbc6d8bdf391e3cbf1ac1e57c554913aa2b3b355f736347e5526634
status: generated
scaffold_hash: eed16125044825f51edb6ed518640ee3d6695302a7e9bb31e8311c530b6ab8fe
---

# Agents

The agents feature is Attune AI's Universal Agent Factory — a single interface for creating, running, and orchestrating AI agents backed by AutoGen, Haystack, LangChain, or LangGraph without rewriting your code when you change the underlying framework.

## Three-layer architecture

Every agent interaction flows through three layers:

1. **Adapter** — A framework-specific adapter (for example, `AutoGenAdapter`, `HaystackAdapter`, or `LangChainAdapter`) implements `BaseAdapter` and handles all communication with the underlying framework. Each adapter exposes `create_agent()`, `create_workflow()`, and `create_tool()`, plus an `is_available()` method that tells you whether the optional framework dependency is installed.

2. **Agent** — The adapter produces a framework-specific agent wrapper — `AutoGenAgent`, `HaystackAgent`, `LangChainAgent`, or `LangGraphAgent` — each implementing `BaseAgent`. Call `invoke()` for a single result or `stream()` for an async generator of incremental responses.

3. **Workflow** — When multiple agents need to collaborate, the adapter produces a coordinating workflow: `AutoGenWorkflow` (backed by AutoGen's GroupChat), `HaystackWorkflow` (backed by Haystack's Pipeline), or `LangChainWorkflow` (backed by LangChain's SequentialChain or custom routing). All workflows expose the same `run()` and `stream()` interface as individual agents.

You configure each layer with `AgentConfig` (for agents) and `WorkflowConfig` (for workflows). `AgentCapability`, `AgentRole`, and `Framework` express what an agent can do, what role it plays, and which framework backs it.

## Framework adapters

Because each framework is an optional dependency, adapters use lazy imports. Call the corresponding accessor function to load the adapter only when you need it:

| Accessor | Adapter class | Underlying framework |
|---|---|---|
| `get_autogen_adapter()` | `AutoGenAdapter` | Microsoft AutoGen (GroupChat) |
| `get_haystack_adapter()` | `HaystackAdapter` | deepset Haystack (Pipeline) |
| `get_langchain_adapter()` | `LangChainAdapter` | LangChain (SequentialChain) |
| `get_langgraph_adapter()` | — | LangGraph (node/runnable) |

Every adapter exposes a `framework_name` property you can inspect at runtime. `HaystackAdapter` also provides `create_document_store()` for setting up a backing store — a capability the other adapters don't expose.

If you want to use a wizard object as an agent without going through a full adapter setup, `wrap_wizard()` converts it into a `WizardAgent` in a single call.

## State persistence and recovery

Long-running or fault-prone workflows need a way to checkpoint progress and resume after a failure. Three components handle this:

- **`AgentStateStore`** — persists `AgentStateRecord` entries, one per agent, so a workflow can resume from a known-good checkpoint rather than restarting from scratch.
- **`AgentExecutionRecord`** — captures the inputs, outputs, and metadata for each individual invocation.
- **`AgentRecoveryManager`** — consults stored records to decide whether to retry, skip, or surface an error when an agent fails mid-workflow.

## Built-in specialized agents

The factory ships agents you can use without any custom adapter configuration:

- **Release preparation** — `ReleaseAgent`, `ReleasePrepTeam`, and `ReleasePrepTeamWorkflow` coordinate a multi-agent release pipeline and emit a `ReleaseReadinessReport`.
- **Code and documentation quality** — `CodeQualityAgent`, `DocumentationAgent`, `SecurityAuditorAgent`, and `TestCoverageAgent` analyze a codebase and report findings.

## Operation decorators

Five decorators add cross-cutting behavior to any agent method:

- `safe_agent_operation(operation_name)` — wraps a method in structured error handling and logging; raises `AgentOperationError` on failure.
- `retry_on_failure(max_attempts, delay, backoff, exceptions)` — retries with exponential backoff and re-raises the last exception once all attempts are exhausted.
- `log_performance(threshold_seconds)` — logs a warning when a method exceeds the specified duration.
- `validate_input(required_fields)` — raises `ValueError` if the input is not a dict or is missing any of the listed fields.
- `with_cost_tracking(operation_type)` — records API cost for the decorated call, tagged with the given operation type.
