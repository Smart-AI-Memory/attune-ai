---
type: faq
name: agents-faq
feature: agents
depth: faq
generated_at: 2026-06-04T23:45:26.759983+00:00
source_hash: 1e0485a1d4d99146ba7b61c353f12a4e84f199551b1b95660a8148e047f01d2f
status: generated
---

# Agents FAQ

## What does the agents feature do?

It provides release agents, state persistence, and recovery. This includes a universal agent factory, framework adapters for AutoGen, Haystack, LangChain, and LangGraph, and built-in tooling for tracking agent execution and recovering from failures.

## Which frameworks does agents support?

AutoGen, Haystack, LangChain, and LangGraph. Each has a dedicated adapter class (`AutoGenAdapter`, `HaystackAdapter`, `LangChainAdapter`) and a corresponding lazy-import helper (`get_autogen_adapter()`, `get_haystack_adapter()`, `get_langchain_adapter()`, `get_langgraph_adapter()`).

## How do I get an adapter for my framework?

Call the lazy-import helper for your framework. For example, call `get_langchain_adapter()` to get a `LangChainAdapter`, then use `create_agent(config)` or `create_workflow(config, agents)` on it. All adapters accept a `provider` and an optional `api_key` in their constructors.

## How do I create an agent?

Call `create_agent(config)` on an adapter instance, passing an `AgentConfig`. The method returns a framework-specific agent — for example, `LangChainAgent` or `AutoGenAgent` — that exposes `invoke()` and `stream()` methods.

## How do I run a multi-agent workflow?

Call `create_workflow(config, agents)` on an adapter, passing a `WorkflowConfig` and a list of `BaseAgent` instances. Then call `run()` or `stream()` on the returned workflow object.

## Can I wrap an existing wizard as an agent?

Yes. Call `wrap_wizard(wizard, name, model_tier)` to get back a `WizardAgent`. The `model_tier` parameter defaults to `'capable'`.

## How do I add retry logic to an agent operation?

Decorate your function with `retry_on_failure(max_attempts, delay, backoff, exceptions)`. It retries with exponential backoff and re-raises the last exception if all attempts fail.

## How do I guard against unexpected errors in an agent operation?

Apply the `safe_agent_operation(operation_name)` decorator. It adds logging and error handling and raises `AgentOperationError` on failure.

## How do I track which inputs are required before calling an agent?

Use the `validate_input(required_fields)` decorator. It raises `ValueError` if the input is not a dict or if any field in `required_fields` is missing.

## How do I track API costs?

Decorate your function with `with_cost_tracking(operation_type)`. The `operation_type` parameter defaults to `'agent_call'`.

## How do I debug a failing agent call?

Run `pytest -k "agents" -v` first. If the tests pass but your code still fails, add a `logger.debug` statement at the suspected failure point and re-run with logging enabled. For symptom-based diagnosis, see the troubleshooting page for this feature.

## Where does the agents source code live?

- `src/attune/agents/**` — release agents, state persistence, and recovery
- `src/attune/agent_factory/**` — universal agent factory and framework adapters

**Tags:** `agents`, `ai`, `release`
