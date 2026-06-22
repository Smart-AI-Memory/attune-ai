---
type: concept
name: cli-concept
feature: cli
depth: concept
generated_at: 2026-06-22T09:48:39.757537+00:00
source_hash: 164b677043cfbe05cdc85850c811ec14af92dabac3c48dced21fedf0c3c58146
status: generated
---

# The attune CLI

The attune CLI is the single entry point — `attune.cli_minimal.main` — that parses your arguments, dispatches them to the right command handler, and returns a numeric exit code your shell can act on.

## Structural overview

The CLI splits into two distinct layers that work together:

**Command dispatch** — `create_parser()` builds the argument parser and maps subcommands to handler functions. Every handler follows the same contract: it receives an `argparse.Namespace` and returns an `int` exit code. Workflow-backed commands go through `run_workflow_with_exit_code`, which instantiates a workflow class, runs it, and converts the result into the documented exit code contract for `attune workflow run`.

**Input routing** — `HybridRouter` sits alongside the dispatch layer to handle natural-language or shorthand input. When a user types something that isn't a slash command (detected by `is_slash_command()`), `route_user_input()` translates it into a Claude Code skill invocation. The router learns your habits: each time you invoke `learn_preference(keyword, skill)`, it stores a `RoutingPreference` entry that raises the confidence score for that keyword-to-skill mapping on future calls. `get_suggestions(partial)` uses those stored preferences to offer completions as you type.

## Command groups

The handler functions are organized into focused modules:

| Group | Example commands | What they do |
|---|---|---|
| **Workflows** | `cmd_workflow_run`, `cmd_workflow_list`, `cmd_workflow_info` | Run and inspect registered workflows |
| **Memory** | `cmd_remember`, `cmd_forget`, `cmd_memory_recall`, `cmd_memory_topics`, `cmd_memory_capture`, `cmd_memory_forget_topic`, `cmd_lessons` | Read and write the Redis-backed lesson store |
| **Costs** | `cmd_costs`, `cmd_costs_today`, `cmd_costs_export`, `cmd_costs_reset` | Report, export, and clear cost-tracking data |
| **Telemetry** | `cmd_telemetry_show`, `cmd_telemetry_savings`, `cmd_telemetry_routing_stats`, `cmd_telemetry_models`, `cmd_telemetry_agents`, `cmd_telemetry_signals`, `cmd_telemetry_status`, `cmd_telemetry_enable`, `cmd_telemetry_disable` | Inspect routing and model-usage telemetry, and control the opt-in usage ping |
| **Providers** | `cmd_provider_show`, `cmd_provider_set` | View and change the active model provider |
| **Patterns** | `cmd_patterns_review`, `cmd_patterns_promote`, `cmd_patterns_reject` | Curate promoted code patterns |
| **Utility** | `cmd_setup`, `cmd_validate`, `cmd_version`, `cmd_doctor`, `cmd_features` | Diagnose, configure, and inspect the installation |
| **Help** | `cmd_help` | Browse attune-help documentation templates |
| **Curator** | `cmd_curator` | Render the project briefing in the terminal |

## Routing preferences

`RoutingPreference` is the unit of learned behavior inside `HybridRouter`. Each preference has five fields:

| Field | Type | Role |
|---|---|---|
| `keyword` | `str` | The input fragment that triggers this preference |
| `skill` | `str` | The Claude Code skill to invoke |
| `args` | `str` | Default arguments passed to the skill |
| `usage_count` | `int` | How many times this mapping has fired |
| `confidence` | `float` | Routing weight (starts at `1.0`, adjusted by usage) |

As `usage_count` grows, the router can weigh this preference more heavily when multiple skills match the same keyword. You can inspect accumulated preferences through `cmd_telemetry_routing_stats` and `cmd_telemetry_routing_check`.

## When the CLI layer matters

You interact with this layer every time you run an `attune` command, but it also matters when you are:

- **Scripting** — all handlers return integer exit codes, so `run_workflow_with_exit_code` gives pipelines a reliable signal to branch on.
- **Extending attune** — adding a new subcommand means writing a handler that accepts `Namespace` and returns `int`, then registering it with `create_parser()`.
- **Debugging routing** — if `HybridRouter` sends input to the wrong skill, `cmd_telemetry_routing_stats` and `cmd_telemetry_routing_check` show you which `RoutingPreference` entries are winning and why.
