---
type: error
name: cli-error
feature: cli
depth: error
generated_at: 2026-06-10T07:07:04.652981+00:00
source_hash: 5b5c949846a62732ae6954c6682e1c7a924430b6ac1efcd58027d681df89d386
status: generated
---

# CLI errors

## Common error signatures

These are the most likely failure categories you'll encounter when running `attune` commands or invoking the CLI programmatically via `main()`.

**Non-zero exit codes from workflow execution**
`run_workflow_with_exit_code()` returns an integer exit code. Any value other than `0` means the workflow failed. The specific code distinguishes a validation failure from a runtime error — check the returned `int` before inspecting logs.

**Unrecognised or malformed arguments**
`create_parser()` raises `SystemExit(2)` when an argument cannot be parsed. This most often happens when a subcommand receives unexpected flags or when a required positional argument is missing.

**Routing failures in `HybridRouter.route()`**
If `route_user_input()` or `HybridRouter.route()` cannot match input to a skill, the returned `dict` may indicate no match rather than raising. A `RoutingPreference` with `confidence: float` below a useful threshold produces low-quality routing silently — check the `confidence` field in the returned dict before acting on it.

**Cost command failures**
`cmd_costs_export()` writes cost data to a file; an `OSError` or `PermissionError` here means the destination path is not writable. `cmd_costs_reset()` always returns `0` on success — a non-zero return signals that the reset did not complete.

**Memory command failures**
`cmd_remember()` and `cmd_forget()` operate on a lessons file. A `FileNotFoundError` or `PermissionError` means the file path is missing or not writable. `cmd_forget()` requires a valid line number or keyword — passing neither produces an argument error.

---

## Where errors originate

The following functions are the primary failure points. When an `attune` command misbehaves, the root cause is almost always in one of these:

| Function | Module | What can go wrong |
|---|---|---|
| `run_workflow_with_exit_code()` | `cli_commands._exit_codes` | Workflow raises an unhandled exception; exit code is non-zero |
| `cmd_costs_export()` | `cli_commands.cost_commands` | Destination file not writable (`OSError`, `PermissionError`) |
| `cmd_costs_reset()` | `cli_commands.cost_commands` | Returns non-zero if reset did not complete |
| `cmd_remember()` / `cmd_forget()` | `cli_commands.memory_commands` | Lessons file missing or not writable; bad line number or keyword |
| `HybridRouter.route()` | `attune.cli_router` | Low `confidence` match; no skill matched for the given input |
| `main()` | `attune.cli_minimal` | `SystemExit` on bad arguments; propagates exit code to the shell |

---

## How to diagnose

1. **Check the exit code first.** Every command function returns an `int`. A non-zero value is the primary signal that something failed. For `run_workflow_with_exit_code()`, the exit code encodes the failure category — don't skip past it to the logs.

2. **Identify which command failed.** The subcommand name tells you which module to investigate. Cost commands live in `cli_commands.cost_commands`; memory commands in `cli_commands.memory_commands`; routing in `attune.cli_router`.

3. **Inspect the `RoutingPreference` fields when routing misbehaves.** If `HybridRouter.route()` sends input to the wrong skill, check the stored `RoutingPreference` for that keyword: low `confidence`, wrong `skill`, or a stale `args` value are the most common causes. Use `HybridRouter.get_suggestions()` to see what the router currently matches for a partial input.

4. **Run `attune doctor` (`cmd_doctor`).** This command runs environment checks and surfaces configuration problems that cause multiple CLI commands to fail in non-obvious ways.

5. **Run `attune validate` (`cmd_validate`).** Use this to confirm that your configuration is well-formed before re-running the failing command.

6. **Re-run with a full traceback.** If a command raises rather than returning a non-zero code, the traceback names the exact file and line. The most actionable line is usually the innermost frame inside `cli_commands/` or `cli_router.py`.

---

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

**Tags:** `cli`, `commands`
