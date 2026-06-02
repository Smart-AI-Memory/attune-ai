---
type: error
name: hooks-error
feature: hooks
depth: error
generated_at: 2026-06-02T10:56:02.704265+00:00
source_hash: 4690cd16c282bccaee1ffc3de0ea189b194fa0d71b87cec08e2f3675e136bbb9
status: generated
---

# Hooks errors

## Common error signatures

Errors in the hook system typically fall into three categories:

- **Configuration errors** — `HookConfig.from_yaml()` raises when the YAML file is missing, malformed, or contains an unrecognized `HookEvent` or `HookType` value.
- **Executor errors** — `HookExecutor.execute()` or `HookExecutorSync.execute()` raises when a `HookDefinition` references a Python handler name that was not registered in the `python_handlers` dict passed to the constructor.
- **Registry dispatch errors** — `HookRegistry.fire()` or `HookRegistry.fire_sync()` raises when an event fires but the underlying executor fails, or when `register()` is called with an invalid `priority` or a `HookMatcher` whose `matches()` method raises unexpectedly.
- **Script hook errors** — `run_evaluate_session()`, `apply_learned_patterns()`, or `run_pre_compact()` raises when the `context` dict is missing expected keys, or when `initialize_project()` cannot create the required `.attune` subdirectories.

## Where errors originate

The following functions are the most common raise sites. The symptom you observe upstream — a hook silently not firing, a `fire()` call returning no results, or a script handler crashing — usually traces back to one of these:

- `HookConfig.from_yaml()` — fails fast if the YAML path does not exist or the file does not parse into a valid `HookConfig`.
- `HookExecutor.execute()` / `HookExecutorSync.execute()` — fails if the `HookDefinition` requests a Python handler that is absent from `python_handlers`.
- `HookRegistry.fire()` / `HookRegistry.fire_sync()` — propagates executor errors for every matching rule; inspect `get_execution_log()` immediately after a failed `fire()` call to see which rules ran and which did not.
- `run_evaluate_session()` / `apply_learned_patterns()` — fail when the `context` dict passed by the hook lifecycle is incomplete.
- `initialize_project()` — fails with a filesystem error if the process lacks write permission to create directories under `INIT_DIRECTORIES` (`.attune`, `.attune/sessions`, etc.).

## How to diagnose

1. **Read the execution log first.** Call `HookRegistry.get_execution_log()` (optionally with `event_filter`) immediately after a failed `fire()` or `fire_sync()` call. The log shows which `HookRule` and `HookDefinition` were attempted and where execution stopped.

2. **Check `get_stats()` for silent failures.** If `fire()` returns an empty list when you expected results, call `HookRegistry.get_stats()` to verify that hooks are registered for the event and that the `HookMatcher.matches()` call is returning `True` for your context.

3. **Validate your `HookConfig` in isolation.** Load the config with `HookConfig.from_yaml()` and call `get_hooks_for_event()` for the relevant `HookEvent` before wiring it into a `HookRegistry`. This confirms the YAML parsed correctly and the right rules are present.

4. **Verify Python handler registration.** If the error message indicates an unresolved handler, confirm that every handler name referenced in your `HookDefinition` objects appears as a key in the `python_handlers` dict you passed to `HookExecutor` or `HookExecutorSync`.

5. **Check context keys for script hooks.** `run_evaluate_session()`, `apply_learned_patterns()`, and `run_pre_compact()` all receive a `context: dict[str, Any]`. Print the context dict at the call site and compare it against the keys the script expects — missing keys are the most common cause of `KeyError` in these handlers.

## Source files

- `src/attune/hooks/**`

**Tags:** `hooks`, `webhooks`, `events`, `automation`
