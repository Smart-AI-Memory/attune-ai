---
type: warning
name: cli-warning
feature: cli
depth: warning
generated_at: 2026-05-16T06:19:45.819463+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# CLI cautions

## What to watch for

The `attune` CLI spans cost tracking, help browsing, lesson management, memory capture, and provider routing. The risks below are specific to how these commands interact with persistent state and the `HybridRouter` preference store.

## Risk areas

### `cmd_costs_reset()` is irreversible

`cmd_costs_reset()` clears **all** cost tracking data and always returns `0`, so a successful exit code gives you no confirmation that data existed before it was deleted. Run `cmd_costs_export()` to back up data before calling reset, especially in scripts where the call might be unintentional.

### `HybridRouter` preference drift over time

`HybridRouter.learn_preference()` writes to a file-backed store (default path controlled by `preferences_path`). Repeated calls with the same `keyword` accumulate `usage_count` and adjust `confidence`, which changes future routing decisions from `route()`. If you pass `None` for `preferences_path`, the router silently uses a default location — preferences learned in one environment carry over to another if that path is shared (for example, a mounted home directory in a container).

### Cost export overwrites without prompting

`cmd_costs_export()` exports cost data to a file. If the target file already exists, the command does not prompt for confirmation before overwriting it. Specify a unique or timestamped output path when automating exports.

### Lesson and memory commands modify files in place

`cmd_remember()`, `cmd_forget()`, and `cmd_memory_capture()` all write to lesson or memory files directly. `cmd_forget()` removes entries by line number, so line numbers shift after each deletion — running it twice in a loop without re-querying `cmd_lessons()` between calls removes the wrong entries.

### `_CATEGORIES` is internal and subject to change

The `_CATEGORIES` tuple (`errors`, `warnings`, `tips`, `references`) drives filtering in help commands. It is underscore-prefixed and not part of the public API. If your tooling parses CLI output and expects exactly these four category names, a refactor can break it silently.

## How to avoid problems

1. **Export before reset.** Always call `cmd_costs_export()` with a safe output path before `cmd_costs_reset()`. The reset returns `0` regardless of how much data it deletes.

2. **Pin `preferences_path` explicitly.** When constructing `HybridRouter` in tests or containerized environments, pass an explicit `preferences_path` pointing to a temporary or isolated file. Relying on the default path risks cross-environment preference bleed.

3. **Re-query line numbers between `cmd_forget()` calls.** If you need to remove multiple lessons, call `cmd_lessons()` after each `cmd_forget()` to get the updated line numbers before the next deletion.

4. **Use only public API functions.** Depend on the functions listed in `__all__` for each module. Private helpers — anything prefixed with `_`, including `_CATEGORIES` — can change without notice.

5. **Scope cost-command tests carefully.** `cmd_costs_reset()` in a test that shares state with other tests will delete real data. Use a temporary directory or mock the storage layer when testing cost commands.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

**Tags:** `cli`, `commands`
