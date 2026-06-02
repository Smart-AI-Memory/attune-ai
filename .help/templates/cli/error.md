---
type: error
name: cli-error
feature: cli
depth: error
generated_at: 2026-06-02T10:56:02.717530+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# CLI errors

## Common error signatures

CLI failures fall into three categories: commands that exit with a non-zero return code, routing failures where `route_user_input()` or `HybridRouter.route()` cannot match input to a skill, and argument errors where a required field on the `Namespace` object is missing or has an unexpected type.

Specific situations to watch for:

- **`cmd_costs_export` fails silently** — the export target path may be unwritable or the cost data store may be empty. Check file permissions and run `cmd_costs` first to confirm data exists.
- **`cmd_forget` removes the wrong lesson** — `cmd_forget` operates by line number or keyword. If the lessons file has changed since you last ran `cmd_lessons`, the line numbers may no longer match. Run `cmd_lessons` immediately before `cmd_forget` to get current line numbers.
- **`HybridRouter.route()` returns an unexpected result** — a `RoutingPreference` with a low `confidence` value (below `1.0`) or a `usage_count` of `0` may cause the router to select an unintended skill. Inspect the returned dict and check stored preferences with `HybridRouter.get_suggestions()`.
- **`cmd_memory_recall` returns nothing** — the search term may not match any stored content, or the memory file targeted by `cmd_memory_capture` may be in a different location than expected.

## Where errors originate

The following command functions each return an `int` exit code. A return value other than `0` indicates failure — trace the non-zero code back to the specific command to narrow the cause.

| Function | Module | Purpose |
|---|---|---|
| `cmd_costs()` | `cli_commands.cost_commands` | Show cost report for recent period |
| `cmd_costs_today()` | `cli_commands.cost_commands` | Show today's cost summary |
| `cmd_costs_export()` | `cli_commands.cost_commands` | Export cost data to file |
| `cmd_costs_reset()` | `cli_commands.cost_commands` | Clear all cost tracking data |
| `cmd_help()` | `cli_commands.help_commands` | Handle the `attune help` command |
| `cmd_remember()` | `cli_commands.memory_commands` | Add a lesson to the lessons file |
| `cmd_forget()` | `cli_commands.memory_commands` | Remove a lesson by line number or keyword |
| `cmd_lessons()` | `cli_commands.memory_commands` | List current lessons with line numbers |
| `cmd_memory_capture()` | `cli_commands.memory_commands` | Save content to personal cross-session memory |
| `cmd_memory_recall()` | `cli_commands.memory_commands` | Search personal cross-session memory |
| `route_user_input()` | `attune.cli_router` | Route user input to a skill invocation |

## How to diagnose

1. **Check the integer return code.** Every command function returns an `int`. If you called a command through `main()`, its return value is the exit code. A non-zero value tells you which command failed before you look at any output.

2. **Identify whether the failure is in argument parsing or command execution.** `create_parser()` in `attune.cli_minimal` handles argument parsing. If the error occurs before your command function is called, the `Namespace` object passed to it may be incomplete — print `args` at the top of the failing command function to confirm all expected fields are present.

3. **For routing failures, inspect the `RoutingPreference` fields.** If `HybridRouter.route()` produces an unexpected skill match, retrieve stored preferences and check the `keyword`, `skill`, `confidence`, and `usage_count` fields on the relevant `RoutingPreference`. A preference with `confidence < 1.0` was learned implicitly and may not match your intent. Use `HybridRouter.learn_preference()` to set an explicit mapping.

4. **For memory command failures, confirm the target file path.** `cmd_memory_capture()` and `cmd_memory_recall()` operate on a cross-session memory file. If recall returns no results, verify that capture was directed at the same location by checking the `args` passed to each command.

5. **For cost command failures, verify that data exists before exporting or resetting.** Run `cmd_costs_today()` to confirm the cost store is populated before calling `cmd_costs_export()`. `cmd_costs_reset()` returns `0` even when the store is already empty, so a successful reset does not confirm prior data existed.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

**Tags:** `cli`, `commands`
