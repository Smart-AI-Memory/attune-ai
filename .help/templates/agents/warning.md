---
type: warning
name: agents-warning
feature: agents
depth: warning
generated_at: 2026-06-04T23:45:26.754933+00:00
source_hash: 1e0485a1d4d99146ba7b61c353f12a4e84f199551b1b95660a8148e047f01d2f
status: generated
---

# Agents cautions

## What to watch for

The agents feature spans release automation, state persistence, and multi-framework adapters. The risks below are most likely to surface during integration work and production rollouts.

## Risk areas

### Lazy adapter imports can silently return `None`

`get_langchain_adapter()`, `get_langgraph_adapter()`, `get_autogen_adapter()`, and `get_haystack_adapter()` all use lazy imports. If the underlying framework package is not installed, `is_available()` returns `False` and the adapter may not be usable. Call `is_available()` on the adapter before invoking `create_agent()` or `create_workflow()`, otherwise you will get a runtime failure at the point of first use rather than at startup.

### `wrap_wizard()` silently applies a default model tier

`wrap_wizard(wizard, name, model_tier='capable')` defaults `model_tier` to `'capable'`. If you intend to run the wrapped agent under a cost-constrained tier, you must pass `model_tier` explicitly. Omitting it will not raise an error, so cost overruns from unintended tier selection can go unnoticed until billing review.

### `safe_agent_operation` swallows errors as `AgentOperationError`

The `@safe_agent_operation` decorator catches exceptions and re-raises them as `AgentOperationError`. If you nest decorated operations, the original exception type is lost at each layer. Preserve the original error in your exception handling and log the full chain before it is wrapped.

### `retry_on_failure` can multiply API costs

`retry_on_failure(max_attempts=3, delay=1.0, backoff=2.0)` retries on any exception in the `exceptions` tuple. If you include broad exception types such as `Exception`, transient network errors and genuine model errors both trigger retries — up to three billable API calls per invocation. Scope the `exceptions` tuple to the specific retriable error types your framework raises.

### `validate_input` rejects non-dict inputs without a framework-specific message

`@validate_input(required_fields)` raises `ValueError` with the message `'Input must be a dict, got {...}'` when `input_data` is a string. The `invoke()` methods on `AutoGenAgent`, `HaystackAgent`, and `LangChainAgent` accept `str | dict`, but the decorator does not. If you apply `validate_input` to a method that advertises string input, callers will hit an undocumented `ValueError`.

### Agent state records are not automatically recovered

`AgentStateStore` and `AgentRecoveryManager` persist execution state, but recovery is not triggered automatically on agent restart. If a release workflow exits mid-run, you must explicitly invoke recovery through `AgentRecoveryManager` before re-running. Skipping this step can cause `ReleasePrepTeamWorkflow` to reprocess completed stages or miss state that was recorded before the failure.

## How to avoid problems

1. **Check adapter availability at startup.** Call `is_available()` immediately after obtaining an adapter from any of the `get_*_adapter()` functions. Fail fast with a clear message rather than letting the error surface during a workflow run.

2. **Be explicit with `wrap_wizard()` model tier.** Always pass `model_tier` by name — for example, `wrap_wizard(wizard, name="my-agent", model_tier="efficient")` — so the tier is visible at the call site and not hidden in a default.

3. **Narrow the `exceptions` tuple in `retry_on_failure`.** Restrict retries to the specific exception classes that represent transient failures in your framework, rather than catching `Exception` broadly.

4. **Run recovery before re-executing interrupted workflows.** After any unclean shutdown, use `AgentRecoveryManager` to inspect and restore state from `AgentStateStore` before calling `ReleasePrepTeamWorkflow.run()` again.

5. **Avoid depending on private helpers.** Functions and methods prefixed with `_` (such as `_run_command`) are not part of the public API and can change without notice. Use only the names exported in `__all__`.

## Source files

- `src/attune/agents/**`
- `src/attune/agent_factory/**`

**Tags:** `agents`, `ai`, `release`
