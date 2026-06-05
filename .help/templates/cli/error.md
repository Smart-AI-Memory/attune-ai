---
type: error
name: cli-error
feature: cli
depth: error
generated_at: 2026-06-04T23:39:47.647790+00:00
source_hash: 4b177dd28a8ce19bb06606b9ae39e4fe255d7f2fe854f3376d3330f151f3ffac
status: generated
---

# CLI errors

This page covers failures that occur during command dispatch, workflow execution, routing, and memory or cost command handling.

## Common error signatures

Non-zero exit codes are the primary signal that something went wrong. Each command function returns an `int` — a non-zero value means the command failed. Beyond exit codes, watch for these failure patterns:

- `run_workflow_with_exit_code()` returns a non-zero exit code when a workflow fails to instantiate or execute. The returned integer is the contract exit code for `attune workflow run`.
- `cmd_costs_reset()` always returns `0` on success. Any other return value indicates a failure to clear cost tracking data.
- `cmd_forget()` fails when the line number or keyword passed to it doesn't match an existing lesson entry.
- `HybridRouter.route()` may produce unexpected routing when a `RoutingPreference` has a low `confidence` value or a `usage_count` of `0`, meaning the preference has never been reinforced.

## Where errors originate

Failures tend to cluster in three areas:

**Workflow execution** — `run_workflow_with_exit_code()` in `cli_commands/_exit_codes.py` is the boundary between the CLI and workflow logic. A failure here means the workflow either couldn't be instantiated or raised during execution. Check the `workflow_cls` type and the shape of `input_data`.

**Cost commands** — `cmd_costs()`, `cmd_costs_today()`, `cmd_costs_export()`, and `cmd_costs_reset()` in `cli_commands/cost_commands.py` depend on cost tracking state being present and readable. `cmd_costs_export()` additionally requires a writable output path.

**Memory commands** — `cmd_remember()`, `cmd_forget()`, `cmd_lessons()`, and `cmd_memory_capture()` in `cli_commands/memory_commands.py` read from and write to the lessons file. Missing files, malformed line numbers, or unknown keywords are common causes of failure here.

## How to diagnose

1. **Check the exit code first.** Every command in this CLI returns an `int`. A non-zero return from `main()` in `attune.cli_minimal` means at least one command handler returned failure. Identify which command ran and trace it to the specific handler — for example, `cmd_workflow_run()` calls `run_workflow_with_exit_code()`, so a failure there points to workflow instantiation or execution.

2. **Inspect routing output for unexpected dispatch.** If `attune` ran the wrong command, call `route_user_input()` from `attune.cli_router` directly with the same input. Check whether `is_slash_command()` returns the value you expect. If `HybridRouter.route()` is in use, inspect the matching `RoutingPreference` — a low `confidence` or zero `usage_count` on the matched preference means the router is guessing. Use `HybridRouter.learn_preference()` to reinforce the correct mapping.

3. **Narrow memory command failures to the operation.** `cmd_forget()` requires either a valid line number or a keyword that exists in the lessons file — passing an unrecognized value is the most common cause of failure. Run `cmd_lessons()` first to see current entries with their line numbers, then retry the forget operation with a confirmed value.

4. **Check the workflow input shape for `run_workflow_with_exit_code()`.** This function takes `input_data: dict[str, Any]`. If the workflow raises during instantiation, the `input_data` keys are likely mismatched against what `workflow_cls` expects. Enable `json_mode=True` to capture structured output that may include error detail.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/_exit_codes.py`
- `src/attune/cli_commands/cost_commands.py`
- `src/attune/cli_commands/memory_commands.py`
- `src/attune/cli_commands/workflow_commands.py`

**Tags:** `cli`, `commands`
