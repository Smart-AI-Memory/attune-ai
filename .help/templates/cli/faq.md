---
type: faq
name: cli-faq
feature: cli
depth: faq
generated_at: 2026-06-02T10:56:02.734380+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# CLI FAQ

## What does the CLI feature do?

It provides the command-line interface and input routing for attune. This includes commands for cost tracking, memory, telemetry, workflows, and provider configuration, plus the `HybridRouter` that dispatches user input to the right skill.

## How do I start the CLI?

Call `main()` from `attune.cli_minimal`. You can also call `create_parser()` directly if you need to build on top of the argument parser without invoking the full entry point.

## How does routing work?

`route_user_input()` in `attune.cli_router` takes a string of user input and an optional context dict, then returns a routing result dict. Under the hood it uses `HybridRouter`, which you can instantiate directly if you want to manage routing preferences yourself or call `get_suggestions()` for partial-input completion.

## What is a RoutingPreference?

A `RoutingPreference` is a dataclass in `attune.cli_router` that records a learned mapping from a keyword to a skill. Its fields are `keyword`, `skill`, `args` (default `''`), `usage_count` (default `0`), and `confidence` (default `1.0`). You add one by calling `HybridRouter.learn_preference(keyword, skill, args)`.

## How do I check whether a string is a slash command?

Call `is_slash_command(text)` from `attune.cli_router`. It returns a bool.

## Which commands track costs?

Four commands live in `cli_commands.cost_commands`:

- `cmd_costs` — show a cost report for a recent period
- `cmd_costs_today` — show today's cost summary
- `cmd_costs_export` — export cost data to a file
- `cmd_costs_reset` — clear all cost tracking data

## How do I work with memory and lessons?

`cli_commands.memory_commands` exposes seven commands: `cmd_remember`, `cmd_forget`, `cmd_lessons`, `cmd_memory_capture`, `cmd_memory_recall`, `cmd_memory_topics`, and `cmd_memory_forget_topic`. Use `cmd_lessons` to list current lessons with line numbers, `cmd_remember` to add one, and `cmd_forget` to remove one by line number or keyword.

## What telemetry commands are available?

`cli_commands.telemetry_commands` provides `cmd_telemetry_show`, `cmd_telemetry_savings`, `cmd_telemetry_export`, `cmd_telemetry_routing_stats`, `cmd_telemetry_routing_check`, `cmd_telemetry_models`, `cmd_telemetry_agents`, and `cmd_telemetry_signals`.

## How do I run workflows from the CLI?

Use the three commands in `cli_commands.workflow_commands`: `cmd_workflow_list` to see available workflows, `cmd_workflow_info` to inspect one, and `cmd_workflow_run` to execute it.

## How do I check that my setup is valid?

Run `cmd_doctor` or `cmd_validate` from `cli_commands.utility_commands`. Use `cmd_setup` for initial configuration and `cmd_features` to see which features are active.

## How do I debug a failing CLI command?

Run `pytest -k "cli" -v` first. If the tests pass but your code still fails, add a `logger.debug` statement at the suspected failure point and re-run with logging enabled. For symptom-based issues, see the troubleshooting page for this feature.

## Where are the source files?

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

**Tags:** `cli`, `commands`
