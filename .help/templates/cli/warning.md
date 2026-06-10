---
type: warning
name: cli-warning
feature: cli
depth: warning
generated_at: 2026-06-10T07:07:04.659591+00:00
source_hash: 5b5c949846a62732ae6954c6682e1c7a924430b6ac1efcd58027d681df89d386
status: generated
---

# CLI Cautions

## Exit codes carry a contract

`run_workflow_with_exit_code()` in `cli_commands._exit_codes` returns an integer that callers treat as a shell exit code. If you wrap or re-invoke this function and swallow its return value, the process exits `0` even when the workflow failed. Always propagate the return value up to `main()`.

The `on_result` parameter is optional (`None` by default). If you pass a callback, it fires before the exit code is returned — a side effect that is easy to miss when reading the call site.

## `cmd_costs_reset` permanently clears all cost data

`cmd_costs_reset()` returns `0` on success and provides no confirmation prompt. Running it by mistake discards every tracked cost record with no built-in undo. Before automating any script that calls this command, verify that cost data has been exported first with `cmd_costs_export()`.

## Learned routing preferences persist across sessions

`HybridRouter.learn_preference()` writes a `RoutingPreference` entry to disk (at the path supplied to `__init__`). Fields like `usage_count` and `confidence` accumulate over time. If you call `learn_preference()` in a test or a one-off script without pointing `preferences_path` to a throwaway location, you silently mutate the user's live routing preferences.

The `RoutingPreference` dataclass has a `confidence` field (default `1.0`) that `HybridRouter.route()` reads when selecting a skill. Injecting preferences with arbitrary confidence values can cause `route()` to override user intent in ways that are hard to trace.

## Slash-command detection happens before routing

`is_slash_command()` in `attune.cli_router` runs before `route_user_input()` dispatches input. If you pre-process or strip leading characters from user input before passing it to `route_user_input()`, a `/command` string may not be recognized as a slash command, and the router silently falls back to keyword matching instead of raising an error.

## `cmd_costs_export` and `cmd_telemetry_export` write files silently

Both export commands return `0` on success without printing the output path unless the caller's `print_result` callback does so. In automated pipelines, check the destination explicitly after the call — a missing file indicates a failure that the exit code alone may not surface.

## How to reduce risk

1. **Always capture and propagate return values.** Every command function in `cli_commands` returns an `int`. Discard it and you lose the only signal that something went wrong.

2. **Isolate `HybridRouter` in tests.** Pass a temporary file path to `HybridRouter.__init__` in test code so learned preferences don't bleed into the user's real preferences store.

3. **Export before resetting.** Any workflow that calls `cmd_costs_reset()` should call `cmd_costs_export()` first and verify the export succeeded.

4. **Rely on the public API.** Names prefixed with `_` — including `_CATEGORIES` and `_DEFAULT_MODEL` — can change without notice. Depend on the functions listed in `__all__` for `cost_commands` and `memory_commands`.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

**Tags:** `cli`, `commands`
