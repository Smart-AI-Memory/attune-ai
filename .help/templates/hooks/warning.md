---
type: warning
name: hooks-warning
feature: hooks
depth: warning
generated_at: 2026-06-02T10:56:02.710836+00:00
source_hash: 4690cd16c282bccaee1ffc3de0ea189b194fa0d71b87cec08e2f3675e136bbb9
status: generated
---

# Hooks: What to Watch Out For

## Mixing `fire` and `fire_sync` in the same call path

`HookRegistry` exposes two dispatch methods: `fire` and `fire_sync`. Calling `fire_sync` from within an async context — or calling `fire` where the event loop is not running — produces silent failures or deadlocks rather than obvious errors. Decide on one execution model per call path and use `HookExecutorSync` only when you are certain there is no surrounding event loop.

## Priority ordering silently drops hooks when a matcher rejects them

`HookRegistry.register` accepts a `priority` parameter, and `get_matching_hooks` returns only hooks whose `HookMatcher.matches` returns `True` for the current context. A hook registered at high priority but with a narrow matcher will never appear in the results without any error. Before assuming a hook is broken, call `get_matching_hooks` directly with your context dict to verify that the matcher is satisfied.

## `HookConfig.from_yaml` does not validate handler names at load time

When you load a configuration with `HookConfig.from_yaml`, Python-handler names referenced in the YAML are not resolved until `HookExecutor.execute` runs. If you pass a `python_handlers` dict to `HookExecutor` that is missing a name defined in the config, the failure occurs at execution time — potentially mid-session. To catch mismatches early, instantiate `HookExecutor(python_handlers=your_map)` and do a dry-run `execute` call during startup or in your test suite.

## Execution log grows unbounded without explicit management

`HookRegistry.get_execution_log` defaults to returning the last 100 entries, but the underlying log is not automatically capped. In long-running sessions with frequent events, memory usage grows steadily. Call `clear_execution_log` at session boundaries (for example, after `run_pre_compact` completes) or use the `limit` and `event_filter` parameters to keep queries focused.

## `apply_learned_patterns` injects context that affects subsequent hook evaluation

`apply_learned_patterns` generates a context-injection string from learned patterns. If you call this before firing hooks that read from the same context dict, the injected content can change which hooks `HookMatcher.matches` selects. Run `apply_learned_patterns` after hook dispatch if your matchers depend on unmodified session context, or make a copy of the context dict before injection.

## `validate_bash_command` and `validate_file_path` return a tuple, not an exception

`scripts.security_guard.validate_bash_command` and `validate_file_path` both return `tuple[bool, str]`. Callers that check only the boolean and discard the message string lose the reason a command was rejected. Always unpack and log or surface the second element — particularly in hooks that run `validate_bash_command` against tool inputs, where the rejection reason is the actionable signal.

## How to reduce risk

- **Verify matcher behavior before debugging executor behavior.** Call `registry.get_matching_hooks(event, context)` to confirm which hooks are selected before investigating why a hook appears not to run.
- **Audit your `python_handlers` map against your YAML config at startup.** A one-time check when you construct `HookExecutor` prevents silent execution failures later.
- **Use `get_stats` to detect unexpected hook activity.** `HookRegistry.get_stats` gives you a count-level view of dispatch activity. A count that is higher or lower than expected is the fastest indicator that a matcher or priority setting is wrong.
- **Keep context dicts immutable across a single `fire` call.** Pass a copy if any handler or script (such as `apply_learned_patterns`) may mutate the dict mid-dispatch.
