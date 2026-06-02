---
type: comparison
name: hooks-comparison
feature: hooks
depth: comparison
generated_at: 2026-06-02T10:56:02.727042+00:00
source_hash: 4690cd16c282bccaee1ffc3de0ea189b194fa0d71b87cec08e2f3675e136bbb9
status: generated
---

# Comparison: HookRegistry vs HookConfig vs direct HookExecutor

## Overview

The hooks system gives you three distinct entry points for responding to Claude Code lifecycle events. Each suits a different integration style. This page helps you choose the right one.

| Capability | `HookRegistry` | `HookConfig` (YAML) | `HookExecutor` directly |
|---|---|---|---|
| **Registration style** | Programmatic, at runtime | Declarative, from a YAML file | Manual — you supply the `HookDefinition` |
| **Conditional matching** | `HookMatcher` per handler | `HookMatcher` in YAML rules | You evaluate conditions yourself |
| **Priority ordering** | `priority` param on `register()` | `priority` field in YAML | You control execution order |
| **Async execution** | `fire()` | Loaded via `load_config()`, then `fire()` | `HookExecutor.execute()` |
| **Sync execution** | `fire_sync()` | Loaded via `load_config()`, then `fire_sync()` | `HookExecutorSync.execute()` |
| **Execution logging** | `get_execution_log()`, `get_stats()` | Same, once config is loaded into a registry | None built-in |
| **Portable config** | Not portable without code | `from_yaml()` / `to_yaml()` round-trips | Not applicable |
| **Handler type** | Python `Callable` | Python handlers injected at executor init | Python `Callable` in `python_handlers` dict |
| **Best for** | Long-lived services, dynamic registration | Shareable, file-driven configuration | One-off execution or testing a single hook |

## Option details

### `HookRegistry` — runtime dispatch hub

`HookRegistry` is the highest-level interface. It owns the full lifecycle: registration, matching, dispatch, and observability.

```python
from hooks import HookRegistry, HookEvent

registry = HookRegistry()
handler_id = registry.register(
    HookEvent.PRE_TOOL,
    my_handler,
    description="Validate before tool runs",
    priority=10,
)

results = registry.fire(HookEvent.PRE_TOOL, context={"tool": "bash"})
registry.get_execution_log(limit=50, event_filter=HookEvent.PRE_TOOL)
```

Key characteristics:

- `register()` returns a `handler_id` string you can pass to `unregister()` later — useful when handlers need to be swapped at runtime.
- `get_matching_hooks()` lets you inspect which hooks *would* fire for a given context before actually firing them.
- `get_stats()` exposes aggregate execution metrics across all registered hooks.

### `HookConfig` — declarative, file-driven configuration

`HookConfig` is the right choice when you want hook definitions to live outside Python code. Load from or save to YAML with `from_yaml()` and `to_yaml()`.

```python
from hooks import HookConfig, HookEvent

config = HookConfig.from_yaml(".attune/hooks.yaml")
rules = config.get_hooks_for_event(HookEvent.POST_TOOL)

# Or build programmatically and persist
config.add_hook(HookEvent.PRE_TOOL, my_definition, matcher=my_matcher, priority=5)
config.to_yaml(".attune/hooks.yaml")
```

A `HookConfig` on its own does not fire hooks — you load it into a `HookRegistry` via `registry.load_config(config)` to get dispatch and logging.

### `HookExecutor` / `HookExecutorSync` — single-hook execution

`HookExecutor` and its synchronous counterpart `HookExecutorSync` sit at the bottom of the stack. Both expose a single `execute(hook, context)` method. Use them when you have a `HookDefinition` in hand and want to run it without setting up a full registry.

```python
from hooks.executor import HookExecutor, HookExecutorSync

executor = HookExecutor(python_handlers={"my_fn": my_callable})
result = executor.execute(hook_definition, context)

# In a synchronous context:
sync_executor = HookExecutorSync(python_handlers={"my_fn": my_callable})
result = sync_executor.execute(hook_definition, context)
```

There is no built-in logging or matching at this level — you trade observability for simplicity.

## Tradeoffs summary

| Concern | Winner | Notes |
|---|---|---|
| **Simplest setup** | `HookExecutor` / `HookExecutorSync` | No registry, no config — just `execute()` |
| **Best observability** | `HookRegistry` | `get_execution_log()`, `get_stats()`, `event_filter` |
| **Shareable config** | `HookConfig` + YAML | `from_yaml()` / `to_yaml()` make config portable across environments |
| **Dynamic handlers** | `HookRegistry` | `register()` / `unregister()` at runtime without touching files |
| **Sync-only environments** | `HookExecutorSync` or `fire_sync()` | Both paths support synchronous execution |

## Use X when...

**Use `HookRegistry`** when you are building a long-lived service or agent integration that needs to register and unregister handlers dynamically, inspect execution history via `get_execution_log()`, or fire hooks across multiple event types with priority ordering.

**Use `HookConfig` + `from_yaml()`** when hook definitions should be version-controlled, shared across environments, or edited without deploying Python code. Load the config into a `HookRegistry` to get full dispatch and logging on top of it.

**Use `HookExecutor` or `HookExecutorSync`** when you need to run a single known `HookDefinition` in isolation — for example, in a test, a one-off migration script, or a context where standing up a registry is more overhead than the task warrants.

**Avoid wiring up any of these** for purely exploratory work or throwaway scripts. The built-in script functions (`run_evaluate_session()`, `run_pre_compact()`, `check_init()`) already handle the most common lifecycle tasks without requiring you to configure hooks manually.

**Tags:** `hooks`, `webhooks`, `events`, `automation`

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 35 (code fence) | error | `from hooks import …` — module not importable |
| Line 77 (code fence) | error | `from hooks.executor import …` — module not importable |
