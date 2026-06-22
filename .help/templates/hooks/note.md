---
type: note
name: hooks-note
feature: hooks
depth: note
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 92f76c4d4d77b21e59b9a6aed8e65dd221371f5ce10f2941171a5c0310c232c1
status: generated
---

# Note: hooks

The `hooks` package manages lifecycle event dispatch for Attune AI. It exposes five public names at the package boundary: `HookConfig`, `HookDefinition`, `HookEvent`, `HookExecutor`, and `HookRegistry`.

## How the package is structured

Three modules divide the responsibilities:

- **`hooks.config`** defines the data model: `HookEvent` (event types tied to the Claude Code lifecycle), `HookType`, `HookDefinition`, `HookMatcher`, `HookRule`, and `HookConfig`. `HookConfig` is the top-level container; you load it from a YAML file with `HookConfig.from_yaml()` and query it with `get_hooks_for_event()`.

- **`hooks.executor`** runs hook actions. `HookExecutor.execute()` accepts a `HookDefinition` and a context dict and returns a result dict. `HookExecutorSync` wraps the same interface for call sites that cannot use async code.

- **`hooks.registry`** is the dispatch layer. `HookRegistry` holds all registered hooks, matches them against incoming events via `get_matching_hooks()`, and fires them with `fire()` or `fire_sync()`. It also tracks execution history through `get_execution_log()` and exposes aggregate metrics through `get_stats()`.

## Relationship to scripts

The `scripts` package contains Python callables that plug into the registry as handlers. Examples include `run_evaluate_session`, `run_pre_compact`, `check_init`, and `suggest_compact`. You pass these callables to `HookRegistry.register()` as the `handler` argument. The registry assigns each registration a string ID that `unregister()` accepts later.

## Execution log

`HookRegistry.get_execution_log()` returns up to 100 entries by default. Pass `event_filter` to narrow results to a specific `HookEvent`. Call `clear_execution_log()` to reset it between test runs or sessions.
