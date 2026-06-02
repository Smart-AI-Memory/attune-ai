---
type: note
name: cli-note
feature: cli
depth: note
generated_at: 2026-06-02T10:56:02.742270+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# Note: cli

The `cli` feature spans two layers: a set of command handler functions organized by domain, and a routing layer that maps free-form user input to those commands.

## Command handlers

Command handlers live in `cli_commands/` and are grouped by domain. Each function accepts an `argparse.Namespace` and returns an integer exit code.

| Module | Functions |
|---|---|
| `cost_commands` | `cmd_costs`, `cmd_costs_today`, `cmd_costs_export`, `cmd_costs_reset` |
| `memory_commands` | `cmd_remember`, `cmd_forget`, `cmd_lessons`, `cmd_memory_capture`, `cmd_memory_recall`, `cmd_memory_topics`, `cmd_memory_forget_topic` |
| `telemetry_commands` | `cmd_telemetry_show`, `cmd_telemetry_savings`, `cmd_telemetry_export`, `cmd_telemetry_routing_stats`, `cmd_telemetry_routing_check`, `cmd_telemetry_models`, `cmd_telemetry_agents`, `cmd_telemetry_signals` |
| `utility_commands` | `cmd_setup`, `cmd_validate`, `cmd_version`, `cmd_features`, `cmd_doctor` |
| `workflow_commands` | `cmd_workflow_list`, `cmd_workflow_info`, `cmd_workflow_run` |
| `provider_commands` | `cmd_provider_show`, `cmd_provider_set` |
| `help_commands` | `cmd_help` |

The entry point is `attune.cli_minimal.main`, which calls `create_parser` to build the argument parser and then dispatches to the appropriate handler.

## Routing layer

`attune.cli_router` sits above the command handlers and routes free-form text input — including slash commands detected by `is_slash_command` — to the correct skill invocation.

`HybridRouter` is the primary routing class. It accepts an optional `preferences_path` pointing to a file where learned preferences are persisted. Its `route` method returns a `dict` describing the resolved skill and arguments. `get_suggestions` accepts a partial string and returns a ranked list of completions.

Learned preferences are stored as `RoutingPreference` instances:

| Field | Type | Default | Meaning |
|---|---|---|---|
| `keyword` | `str` | — | Trigger word matched against user input |
| `skill` | `str` | — | Skill name to invoke |
| `args` | `str` | `''` | Arguments passed to the skill |
| `usage_count` | `int` | `0` | Times this preference has been applied |
| `confidence` | `float` | `1.0` | Routing confidence score |

`learn_preference(keyword, skill, args)` adds or updates a `RoutingPreference` entry, incrementing `usage_count` over time.

## Relationship between layers

The command handlers and the routing layer are independent at the import level. `cli_router` resolves *which* skill to invoke; `cli_minimal.main` and the `cli_commands` modules handle *how* to execute it once the parser has matched a subcommand. The `route_user_input` convenience function in `attune.cli_router` wraps `HybridRouter.route` for callers that don't need to manage a router instance directly.
