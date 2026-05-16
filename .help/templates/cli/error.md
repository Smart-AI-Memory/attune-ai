---
type: error
name: cli-error
feature: cli
depth: error
generated_at: 2026-05-16T06:19:45.813301+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# CLI errors

CLI errors cover failures in command dispatch, cost tracking, memory management, and help browsing — the entry-point commands that `attune` exposes at the terminal.

## Common error signatures

Errors in the CLI typically fall into one of these categories:

- **Non-zero exit code with no traceback** — a command function such as `cmd_costs()` or `cmd_costs_export()` returned a non-zero integer, signaling failure to the shell without raising an exception.
- **`FileNotFoundError` or `OSError`** — `cmd_costs_export()` or `cmd_memory_capture()` could not read from or write to the target path. Check that the file path exists and that your process has write permission.
- **`ValueError` during argument parsing** — a required argument was missing or had an unexpected format. This commonly surfaces in `cmd_remember()`, `cmd_forget()`, or `cmd_costs_reset()` when the `Namespace` passed by argparse is incomplete.
- **`KeyError` or `IndexError` in memory commands** — `cmd_forget()` references a line number or keyword that does not exist in the lessons file.

## Where errors originate

The following command functions are the primary failure sites. Each maps to a subcommand you invoke at the terminal:

| Function | Subcommand area | Source file |
|---|---|---|
| `cmd_costs()` | Cost report for recent period | `src/attune/cli_commands/cost_commands.py` |
| `cmd_costs_today()` | Today's cost summary | `src/attune/cli_commands/cost_commands.py` |
| `cmd_costs_export()` | Export cost data to file | `src/attune/cli_commands/cost_commands.py` |
| `cmd_costs_reset()` | Clear all cost tracking data | `src/attune/cli_commands/cost_commands.py` |
| `cmd_help()` | `attune help` command | `src/attune/cli_commands/help_commands.py` |
| `cmd_remember()` / `cmd_forget()` / `cmd_lessons()` | Lesson management | `src/attune/cli_commands/` |
| `cmd_memory_capture()` / `cmd_memory_recall()` | Cross-session memory | `src/attune/cli_commands/` |

## How to diagnose

1. **Check the exit code first.** Command functions return `0` on success and a non-zero integer on failure. If `attune` exits silently without a traceback, the function returned an error code rather than raising an exception. Run `echo $?` immediately after the command to confirm.

2. **Identify which subcommand failed.** The error behavior differs by command group. A failure in `cmd_costs_export()` points to a file I/O problem; a failure in `cmd_forget()` points to a bad line number or missing keyword in the lessons file; a failure in `cmd_help()` may indicate a missing or malformed template category (valid values are `errors`, `warnings`, `tips`, and `references`).

3. **Inspect the full traceback.** If an exception was raised, the traceback names the exact file and line in `src/attune/cli_commands/` where execution stopped. Match the file to the table above to narrow the scope.

4. **Verify routing state.** If `HybridRouter` is involved — for example, when a keyword-based dispatch precedes the command call — check the preferences file path passed to `HybridRouter.__init__()`. A missing or unreadable preferences file can prevent routing before any command function runs.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/cost_commands.py`
- `src/attune/cli_commands/help_commands.py`
- `src/attune/cli_commands/` (memory and lesson commands)

**Tags:** `cli`, `commands`
