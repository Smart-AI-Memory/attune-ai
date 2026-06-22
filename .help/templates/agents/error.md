---
type: error
name: agents-error
feature: agents
depth: error
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 4f67c2f70bbc6d8bdf391e3cbf1ac1e57c554913aa2b3b355f736347e5526634
status: generated
---

# Agents errors

## Common error signatures

Failures in the agents feature fall into three categories: input validation errors, framework adapter initialization errors, and agent operation errors.

- `ValueError: Input must be a dict, got {...}` — raised by `validate_input` when an `invoke()` or `run()` call receives a non-dict argument.
- `ValueError: Missing required fields: {...}` — raised by `validate_input` when a required field is absent from the input dict passed to `invoke()` or `run()`.
- `AgentOperationError` — raised by `safe_agent_operation` when a decorated agent method fails. The decorator logs the failure before re-raising, so the log output will describe the operation that failed.
- Framework unavailability — `is_available()` returning `False` on `AutoGenAdapter`, `HaystackAdapter`, or `LangChainAdapter` indicates the optional framework dependency is not installed. Any subsequent call to `create_agent()` or `create_workflow()` on that adapter will fail.
- Retry exhaustion — `retry_on_failure` re-raises the last exception after `max_attempts` attempts. When you see a repeated exception logged multiple times in quick succession, the cause is usually a transient failure that exceeded the retry budget.

## Where errors originate

Errors typically arise at one of the following call sites:

- `get_langchain_adapter()`, `get_langgraph_adapter()`, `get_autogen_adapter()`, `get_haystack_adapter()` — these lazy-import functions fail at call time if the corresponding framework is not installed, not at import time.
- `wrap_wizard()` — wraps a wizard as a `WizardAgent`; fails if the wizard argument is incompatible with `AgentConfig` expectations.
- `AgentRecoveryManager` — manages recovery for failed agent executions; errors here affect `AgentExecutionRecord` and `AgentStateStore` persistence.

## How to diagnose

1. **Check whether the framework adapter is available.** Call `is_available()` on the relevant adapter (`AutoGenAdapter`, `HaystackAdapter`, or `LangChainAdapter`) before calling `create_agent()` or `create_workflow()`. A `False` return means the optional dependency is missing — install it first.

2. **Read the `AgentOperationError` message.** The `safe_agent_operation` decorator logs the operation name and exception details before raising `AgentOperationError`. Check your log output at `ERROR` level for the decorated operation name; it identifies which agent method failed and the underlying cause.

3. **Identify which `validate_input` field is missing.** When you see `ValueError: Missing required fields: {...}`, the set in the message names the exact keys absent from your input dict. Ensure the dict passed to `invoke()` or `run()` includes every field declared in `required_fields` for that decorator.

4. **Check for retry exhaustion.** If `retry_on_failure` has re-raised, you will see the same exception logged `max_attempts` times. Confirm whether the underlying cause is a transient issue (network, rate limit) or a persistent misconfiguration — the latter will not resolve with more retries.

5. **Enable `DEBUG` logging.** The agents module uses Python's `logging` facility. Set the log level to `DEBUG` and re-run the failing scenario. `safe_agent_operation` and `log_performance` both emit structured log entries that trace execution state before and after each operation.

## Source files

- `src/attune/agents/**`
- `src/attune/agent_factory/**`

**Tags:** `agents`, `ai`, `release`
