---
type: faq
name: cli-faq
feature: cli
depth: faq
generated_at: 2026-06-04T23:39:47.658072+00:00
source_hash: 4b177dd28a8ce19bb06606b9ae39e4fe255d7f2fe854f3376d3330f151f3ffac
status: generated
---

# CLI FAQ

## What does the CLI feature do?

It provides the command-line interface for attune, including command dispatch, cost tracking, memory management, telemetry, workflow execution, and input routing via `HybridRouter`.

## How do I start the CLI?

Call `main()` from `attune.cli_minimal`. It accepts an optional `argv` list — pass `None` to read from `sys.argv`.

## How does attune route my input to the right command?

`route_user_input()` in `attune.cli_router` takes a string and an optional context dict and returns a routing decision. For finer control, instantiate `HybridRouter` directly and call its `route()` method.

## Can attune learn my routing preferences?

Yes. Call `HybridRouter.learn_preference(keyword, skill, args)` to teach the router that a particular keyword should map to a skill. The router stores each preference as a `RoutingPreference` with a `usage_count` and a `confidence` score that you can inspect later.

## How do I check whether a string is a slash command?

Call `is_slash_command(text)` from `attune.cli_router`. It returns a boolean.

## What commands are available for cost tracking?

Four commands are available via `cli_commands.cost_commands`:

- `cmd_costs` — show a cost report for the recent period
- `cmd_costs_today` — show today's cost summary
- `cmd_costs_export` — export cost data to a file
- `cmd_costs_reset` — clear all cost tracking data (returns `0` on success)

## How do I work with memory and lessons?

The `cli_commands.memory_commands` module exposes:

- `cmd_remember` — add a lesson to the lessons file
- `cmd_forget` — remove a lesson by line number or keyword
- `cmd_lessons` — list current lessons with line numbers
- `cmd_memory_capture` — save content to personal cross-session memory
- `cmd_memory_recall`, `cmd_memory_topics`, `cmd_memory_forget_topic` — recall, browse, and remove stored topics

## How do I run a workflow from the CLI?

Use `cmd_workflow_run` from `cli_commands.workflow_commands`, or call `run_workflow_with_exit_code()` directly if you need the exit code contract in your own code. Pass the workflow class, an `input_data` dict, a `name`, a `json_mode` flag, and a `print_result` callable.

## What exit codes does the CLI return?

`run_workflow_with_exit_code()` returns the contract exit code for a workflow run. `cmd_costs_reset` returns `0` on success. Individual command functions all return `int` — check the specific command's behavior for non-zero values.

## How do I check whether my setup is correct?

Run `cmd_doctor` from `cli_commands.utility_commands`. You can also run `cmd_validate` to validate configuration and `cmd_setup` to walk through initial setup.

## Where are the source files?

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/`

**Tags:** `cli`, `commands`
