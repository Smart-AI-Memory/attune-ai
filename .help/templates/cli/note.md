---
type: note
name: cli-note
feature: cli
depth: note
generated_at: 2026-06-04T23:39:47.664604+00:00
source_hash: 4b177dd28a8ce19bb06606b9ae39e4fe255d7f2fe854f3376d3330f151f3ffac
status: generated
---

# Note: cli

The `attune` CLI is built from two layers: a routing layer (`attune.cli_router`) that maps user input to skills, and a command layer (`cli_commands.*`) that implements each subcommand.

## Routing layer

`HybridRouter` in `attune.cli_router` maps user input to Claude Code skill invocations. It maintains learned preferences, stored as `RoutingPreference` dataclass instances with the following fields:

| Field | Type | Default | Meaning |
|---|---|---|---|
| `keyword` | `str` | — | Trigger word or phrase |
| `skill` | `str` | — | Skill to invoke |
| `args` | `str` | `''` | Arguments passed to the skill |
| `usage_count` | `int` | `0` | Number of times this preference has fired |
| `confidence` | `float` | `1.0` | Router confidence in this preference |

`route_user_input()` and `is_slash_command()` are the module-level entry points; `HybridRouter` is the stateful class for callers that need learned preferences and tab-completion suggestions via `get_suggestions()`.

## Command layer

Each subcommand group lives in its own module under `cli_commands`:

| Module | Commands |
|---|---|
| `cost_commands` | `cmd_costs`, `cmd_costs_today`, `cmd_costs_export`, `cmd_costs_reset` |
| `memory_commands` | `cmd_remember`, `cmd_forget`, `cmd_lessons`, `cmd_memory_capture`, `cmd_memory_recall`, `cmd_memory_topics`, `cmd_memory_forget_topic` |
| `telemetry_commands` | `cmd_telemetry_show`, `cmd_telemetry_savings`, `cmd_telemetry_export`, `cmd_telemetry_routing_stats`, `cmd_telemetry_routing_check`, `cmd_telemetry_models`, `cmd_telemetry_agents`, `cmd_telemetry_signals` |
| `workflow_commands` | `cmd_workflow_list`, `cmd_workflow_info`, `cmd_workflow_run` |
| `utility_commands` | `cmd_setup`, `cmd_validate`, `cmd_version`, `cmd_features`, `cmd_doctor` |
| `provider_commands` | `cmd_provider_show`, `cmd_provider_set` |
| `help_commands` | `cmd_help` |

Every command function accepts an `argparse.Namespace` and returns an `int` exit code.

## Exit-code contract

`run_workflow_with_exit_code()` in `cli_commands._exit_codes` is the standard way to execute a workflow and map its outcome to a process exit code. `cmd_workflow_run` uses this function to satisfy the exit-code contract for `attune workflow run`.

## Entry point

`attune.cli_minimal` exposes `main()`, `create_parser()`, and `get_version()`. `main()` is the top-level entry point registered in the package's console scripts.
