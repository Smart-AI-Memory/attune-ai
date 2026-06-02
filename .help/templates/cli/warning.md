---
type: warning
name: cli-warning
feature: cli
depth: warning
generated_at: 2026-06-02T10:56:02.727759+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# CLI Cautions

## What to watch for

The CLI layer connects user input to skills and cost tracking through routing logic that learns from use. Two areas deserve attention before you start: destructive commands that cannot be undone, and a routing preference system whose learned state can produce surprising results.

## Risk areas

### `cmd_costs_reset` permanently discards all cost data

`cmd_costs_reset` clears every cost record. There is no confirmation prompt and no undo. If you are scripting cost workflows, call `cmd_costs_export` first to preserve the data before any reset.

### `HybridRouter` learns preferences that silently override routing

`HybridRouter.learn_preference(keyword, skill, args)` writes a `RoutingPreference` to disk (at the path passed to `__init__`). Once written, that preference — including its `confidence` and `usage_count` fields — influences every subsequent call to `HybridRouter.route()`. If you call `learn_preference` in a test or experiment and do not clean up the preferences file, those learned entries will affect routing in other contexts, including production sessions.

To inspect what has been learned, call `HybridRouter.get_suggestions(partial)` with an empty string to see all stored keywords before routing runs.

### `route_user_input` and slash-command detection are order-sensitive

`is_slash_command(text)` determines whether input is dispatched as a slash command or passed through the hybrid router. If your input starts with `/` but is not a registered command, it may be silently dropped or misrouted rather than falling back gracefully. Validate the text with `is_slash_command` before passing it to `route_user_input` when the input source is untrusted or user-supplied.

### Memory commands modify persistent state without a dry-run option

`cmd_memory_capture`, `cmd_remember`, `cmd_forget`, and `cmd_memory_forget_topic` all write to or delete from cross-session memory immediately. `cmd_forget` removes a lesson by line number or keyword — if the lessons file has shifted since you last called `cmd_lessons`, you may delete the wrong entry. Always call `cmd_lessons` immediately before `cmd_forget` to confirm line numbers are current.

## How to avoid problems

1. **Export before reset.** Always run `cmd_costs_export` before `cmd_costs_reset` in any automated script. Treat cost data as append-only until you have a confirmed export.

2. **Isolate learned routing preferences in tests.** Pass a temporary file path to `HybridRouter.__init__` during testing so learned `RoutingPreference` entries do not persist to your real preferences file. Delete the temp file in teardown.

3. **Confirm memory line numbers are fresh.** When scripting `cmd_forget` or `cmd_memory_forget_topic`, call `cmd_lessons` or `cmd_memory_topics` in the same session immediately before the delete call to ensure indices have not shifted.

4. **Check slash-command validity before routing.** Use `is_slash_command(text)` to gate input before passing it to `route_user_input`. This prevents ambiguous input from reaching the router in an unexpected state.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

**Tags:** `cli`, `commands`
