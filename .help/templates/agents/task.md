---
type: task
name: agents-task
feature: agents
depth: task
generated_at: 2026-06-04T23:45:26.739731+00:00
source_hash: 1e0485a1d4d99146ba7b61c353f12a4e84f199551b1b95660a8148e047f01d2f
status: generated
---

# Work with agents

Use agents when you need to create, configure, or extend AI agents with framework adapters, state persistence, and recovery support.

## Prerequisites

- Access to the project source code under `src/attune/agents/` and `src/attune/agent_factory/`
- A working Python environment with your target framework (LangChain, LangGraph, AutoGen, or Haystack) installed

## Steps

1. **Choose and retrieve the right adapter.**
   Call the lazy-import helper for the framework you are targeting:

   - `get_langchain_adapter()` — returns a `LangChainAdapter` for LangChain chains and agent executors
   - `get_langgraph_adapter()` — returns an adapter for LangGraph nodes and runnables
   - `get_autogen_adapter()` — returns an `AutoGenAdapter` for Microsoft AutoGen workflows
   - `get_haystack_adapter()` — returns a `HaystackAdapter` for Haystack pipelines

   Each helper performs a lazy import, so only the dependencies for the framework you choose are loaded.

2. **Create an agent or workflow.**
   Call `create_agent(config)` on the adapter, passing an `AgentConfig` instance. To coordinate multiple agents, call `create_workflow(config, agents)` with a `WorkflowConfig` and a list of `BaseAgent` instances.

   If you are working with a wizard rather than a framework agent, use `wrap_wizard(wizard, name, model_tier)` to produce a `WizardAgent` directly.

3. **Apply decorators to protect your agent operations.**
   Wrap any function that calls an agent with the appropriate decorator from `src/attune/agent_factory/decorators.py`:

   - `safe_agent_operation(operation_name)` — adds structured logging and raises `AgentOperationError` on failure
   - `retry_on_failure(max_attempts, delay, backoff, exceptions)` — retries with exponential backoff; raises the last exception when all attempts are exhausted
   - `log_performance(threshold_seconds)` — logs a warning when the call exceeds the threshold
   - `validate_input(required_fields)` — raises `ValueError` if the input is not a dict or is missing required fields
   - `with_cost_tracking(operation_type)` — records API cost metadata for the call

4. **Invoke the agent.**
   Call `invoke(input_data, context)` for a single synchronous result, or `stream(input_data, context)` to consume an `AsyncGenerator` of incremental response dicts. For workflows, call `run(input_data, initial_state)` or the corresponding `stream` method.

5. **Run the related tests.**
   Verify that your changes do not introduce regressions:

   ```bash
   pytest -k "agents"
   ```

## Key files

- `src/attune/agents/` — release agents, state store, and recovery manager (`AgentStateStore`, `AgentRecoveryManager`, `ReleaseAgent`, `ReleasePrepTeam`)
- `src/attune/agent_factory/adapters/__init__.py` — lazy-import helpers (`get_langchain_adapter`, `get_langgraph_adapter`, `get_autogen_adapter`, `get_haystack_adapter`, `wrap_wizard`)
- `src/attune/agent_factory/adapters/wizard_adapter.py` — `WizardAgent` and `WizardAdapter`
- `src/attune/agent_factory/decorators.py` — `safe_agent_operation`, `retry_on_failure`, `log_performance`, `validate_input`, `with_cost_tracking`

## Verify success

After running your agent call, confirm the following:

- `invoke()` or `run()` returns a `dict` without raising an `AgentOperationError`
- `stream()` yields at least one `dict` chunk before the generator closes
- `pytest -k "agents"` reports zero failures
- If you used `with_cost_tracking`, cost metadata appears in the operation log for the call
