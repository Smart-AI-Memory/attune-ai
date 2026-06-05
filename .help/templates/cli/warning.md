---
type: warning
name: cli-warning
feature: cli
depth: warning
generated_at: 2026-06-04T23:39:47.653380+00:00
source_hash: 4b177dd28a8ce19bb06606b9ae39e4fe255d7f2fe854f3376d3330f151f3ffac
status: generated
---

# CLI Cautions

## Exit codes are a contract — don't swallow them

`run_workflow_with_exit_code()` returns an integer exit code that the shell depends on. If you wrap this function or call `main()` from another process, propagate its return value all the way to `sys.exit()`. Discarding the return value silently reports success to the caller regardless of what the workflow actually did.

`cmd_costs_reset()` always returns `0`, even when invoked unintentionally — there is no confirmation prompt. Once cost tracking data is cleared, it cannot be recovered from within the CLI.

## Learned routing preferences persist across sessions

`HybridRouter.learn_preference()` writes a `RoutingPreference` entry (with fields `keyword`, `skill`, `args`, `usage_count`, and `confidence`) to a preferences file. If `preferences_path` is not explicitly set in `HybridRouter.__init__()`, the router reads and writes a default path. Automated tests that call `learn_preference()` without an isolated `preferences_path` will pollute the shared preferences file, causing `route()` to behave differently on subsequent runs.

## `route_user_input()` and slash-command detection interact

`is_slash_command()` gates whether `route_user_input()` treats input as a slash command or freeform text. Passing input that starts with `/` to `route_user_input()` when you intend freeform routing — or the reverse — produces routing results that bypass the `HybridRouter` preference logic entirely. Check `is_slash_command()` before deciding which path to invoke.

## `cmd_forget()` and `cmd_memory_forget_topic()` are not equivalent

`cmd_forget()` removes a lesson by line number or keyword from the lessons file. `cmd_memory_forget_topic()` removes a topic from cross-session memory. Calling the wrong command silently succeeds while leaving the data you intended to delete untouched. Confirm which store you are targeting before automating either command.

## How to avoid problems

1. **Propagate exit codes.** Always return or pass through the integer that `run_workflow_with_exit_code()` and every `cmd_*` function returns. The exit-code contract is only meaningful if the caller acts on it.

2. **Isolate preferences in tests.** When testing any code that calls `HybridRouter`, pass an explicit temporary `preferences_path` to `HybridRouter.__init__()` so tests cannot read from or write to the shared preferences file.

3. **Distinguish memory stores before deleting.** Use `cmd_memory_topics()` to inspect available topics and `cmd_lessons()` to list lessons before running `cmd_forget()` or `cmd_memory_forget_topic()`. This makes the target explicit.

4. **Rely only on the public API.** Names starting with `_` — including `_exit_codes` internals — can change without notice. Depend on the public functions exported from `cli_commands.cost_commands`, `cli_commands.memory_commands`, and the other `__all__` lists instead.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

**Tags:** `cli`, `commands`
