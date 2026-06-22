---
type: troubleshooting
name: agents-troubleshooting
feature: agents
depth: troubleshooting
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 4f67c2f70bbc6d8bdf391e3cbf1ac1e57c554913aa2b3b355f736347e5526634
status: generated
---

# Troubleshoot agents

## Before you start

This guide covers issues with release agents, state persistence, and recovery. It applies to the adapter layer (`AutoGenAdapter`, `HaystackAdapter`, `LangChainAdapter`) and the agent lifecycle classes (`BaseAgent`, `AgentFactory`, `AgentStateStore`, `AgentRecoveryManager`).

## Symptom table

| If you observe | Check |
|----------------|-------|
| `AgentOperationError` raised | The operation wrapped by `@safe_agent_operation` — the decorator logs the failure before re-raising; check `DEBUG`-level logs for the operation name |
| `ValueError: Missing required fields` | The fields your `invoke()` or `run()` call passes against the list in `@validate_input` — the error message names the missing keys |
| `ValueError: Input must be a dict` | The type of `input_data` passed to `invoke()` or `run()` — these methods expect `str \| dict`, not a list or other type |
| Adapter returns `None` or raises `ImportError` | Whether the framework is installed — call `adapter.is_available()` before `create_agent()` or `create_workflow()` |
| Operation retried unexpectedly or silently swallowed | The `max_attempts`, `delay`, and `backoff` values on `@retry_on_failure` — defaults are 3 attempts, 1.0 s delay, 2.0 backoff |
| Slow agent call with no apparent error | The `threshold_seconds` on `@log_performance` — at `DEBUG` level, the decorator logs calls that exceed the threshold |
| Intermittent failure across runs | State held in `AgentStateStore` from a previous run — inspect or clear stored `AgentStateRecord` entries |

## Diagnosis steps

Work through these in order — each step is cheaper than the one that follows.

### 1. Reproduce in isolation

Reduce your call to the minimum required arguments. For example, to isolate an adapter issue:

```python
from attune.agent_factory.adapters import get_langchain_adapter

adapter = get_langchain_adapter()
print(adapter.is_available())          # False means the framework is not installed
print(adapter.framework_name)          # confirms which adapter you actually got
```

Replace `get_langchain_adapter` with `get_autogen_adapter`, `get_haystack_adapter`, or `get_langgraph_adapter` as appropriate. If `is_available()` returns `False`, install the missing framework before continuing.

### 2. Enable DEBUG logging

Set your log level to `DEBUG` and re-run. The `@safe_agent_operation` decorator logs each operation name and any caught exception before re-raising as `AgentOperationError`. The `@log_performance` decorator logs calls that exceed `threshold_seconds`. Both write at `DEBUG` level and are silent otherwise.

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 3. Validate inputs explicitly

Call the entry point with a known-good `dict` that satisfies `@validate_input`. If you are getting `ValueError: Input must be a dict` or `ValueError: Missing required fields`, the problem is upstream of the agent, not inside it:

- `invoke(input_data, context)` on `AutoGenAgent`, `HaystackAgent`, or `LangChainAgent` — `input_data` must be `str | dict`
- `run(input_data, initial_state)` on `AutoGenWorkflow`, `HaystackWorkflow`, or `LangChainWorkflow` — same constraint

### 4. Check adapter and framework availability

Each adapter exposes `is_available()`. Call it explicitly if you are seeing `ImportError` or unexpected `None` returns:

```python
from attune.agent_factory.adapters import (
    get_autogen_adapter,
    get_haystack_adapter,
    get_langchain_adapter,
)

for getter in [get_autogen_adapter, get_haystack_adapter, get_langchain_adapter]:
    a = getter()
    print(a.framework_name, a.is_available())
```

### 5. Inspect agent state and recovery records

If failures are intermittent and tied to a specific agent identity, check `AgentStateStore` for stale `AgentStateRecord` entries and `AgentRecoveryManager` for unresolved `AgentExecutionRecord` entries from prior runs. Stale state from a previous failed run can cause an otherwise-healthy agent to behave incorrectly.

### 6. Run the test suite

```bash
pytest -k "agents" -v
```

If a test exercises the failing path, use its fixtures as a baseline for your own reproduction. A failing test here confirms the bug is in the library; a passing test suite with a failing integration points to environment or configuration drift.

## Common fixes

**Framework not installed**
`is_available()` returns `False` when the underlying framework package is absent. Install the framework your adapter requires:

```bash
pip install langchain          # for LangChainAdapter / LangChainAgent
pip install pyautogen          # for AutoGenAdapter / AutoGenAgent
pip install haystack-ai        # for HaystackAdapter / HaystackAgent
```

This change is outside the `attune` library itself — the adapter will not work until the dependency is present.

**Missing required fields in `input_data`**
`@validate_input` raises `ValueError: Missing required fields: {...}` and names the missing keys. Add those keys to the `dict` you pass to `invoke()` or `run()`.

**Stale state across runs**
If the agent worked in a previous session and now behaves incorrectly without a code change, clear or reset the `AgentStateStore` entries for that agent. Cached `AgentStateRecord` values from a failed run can cause downstream methods to branch incorrectly.

**Retry loop exhausted**
`@retry_on_failure` re-raises the last exception after `max_attempts` retries (default: 3). If you are hitting this, the root cause is in the exception itself — check `DEBUG` logs for the full traceback from the first attempt. You can increase `max_attempts` or narrow the `exceptions` tuple to avoid masking unrelated errors.

**Version mismatch in a framework dependency**
A framework upgrade can silently change `invoke()` or `run()` call signatures. Confirm the installed version:

```bash
pip show langchain
pip show pyautogen
pip show haystack-ai
```

Pin the version in your requirements file if the adapter was tested against a specific release.

**`wrap_wizard()` producing unexpected behavior**
`wrap_wizard(wizard, name, model_tier)` defaults to `model_tier='capable'`. If the wrapped `WizardAgent` is behaving differently than the underlying wizard, check that `model_tier` matches what the wizard expects and that `name` is set explicitly when you need a stable identifier.

## Source files

- `src/attune/agents/**`
- `src/attune/agent_factory/**`

**Tags:** `agents`, `ai`, `release`
