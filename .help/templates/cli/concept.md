---
type: concept
name: cli-concept
feature: cli
depth: concept
generated_at: 2026-06-04T23:39:47.633186+00:00
source_hash: 4b177dd28a8ce19bb06606b9ae39e4fe255d7f2fe854f3376d3330f151f3ffac
status: generated
---

# CLI

The `attune` CLI is the command-line surface that lets you run workflows, inspect telemetry and costs, manage memory, and configure providers — all through a single entry point defined in `attune.cli_minimal`.

## How the pieces fit together

The CLI has two distinct layers that work in tandem.

**The command layer** is built around `create_parser()` and `main()` in `attune.cli_minimal`. When you invoke `attune`, `main()` parses your arguments and delegates to one of the command modules:

| Module | Commands |
|--------|----------|
| `cli_commands.workflow_commands` | `cmd_workflow_list`, `cmd_workflow_info`, `cmd_workflow_run` |
| `cli_commands.cost_commands` | `cmd_costs`, `cmd_costs_today`, `cmd_costs_export`, `cmd_costs_reset` |
| `cli_commands.memory_commands` | `cmd_remember`, `cmd_forget`, `cmd_lessons`, `cmd_memory_capture`, `cmd_memory_recall`, `cmd_memory_topics`, `cmd_memory_forget_topic` |
| `cli_commands.telemetry_commands` | `cmd_telemetry_show`, `cmd_telemetry_savings`, `cmd_telemetry_export`, `cmd_telemetry_routing_stats`, `cmd_telemetry_routing_check`, `cmd_telemetry_models`, `cmd_telemetry_agents`, `cmd_telemetry_signals` |
| `cli_commands.provider_commands` | `cmd_provider_show`, `cmd_provider_set` |
| `cli_commands.utility_commands` | `cmd_setup`, `cmd_validate`, `cmd_version`, `cmd_features`, `cmd_doctor` |
| `cli_commands.help_commands` | `cmd_help` |

Every command function takes an `argparse.Namespace` and returns an integer exit code.

**The routing layer** sits in `attune.cli_router` and handles free-form or slash-command input. When you type a slash command, `is_slash_command()` detects it. `route_user_input()` then resolves the input to a Claude Code skill invocation. Under the hood, `HybridRouter` does this resolution and can learn from your usage over time.

## Exit-code contract

`run_workflow_with_exit_code()` in `cli_commands._exit_codes` is the bridge between a workflow class and the shell. It instantiates and executes the workflow, then returns a standardised integer that your shell or CI pipeline can act on. All `cmd_*` functions follow the same contract: return `0` on success, non-zero on failure.

## Routing preferences

`HybridRouter` personalises routing by building a set of `RoutingPreference` entries. Each entry captures a `keyword`, the `skill` it should map to, optional `args`, and two learned fields — `usage_count` and `confidence` — that improve over time as you use `learn_preference()`. You can call `get_suggestions()` with a partial string to see what the router would suggest completing.

```python
router = HybridRouter(preferences_path="~/.attune/prefs.json")
router.learn_preference(keyword="deploy", skill="run-deploy-workflow")
router.get_suggestions("dep")   # returns completions ranked by confidence
```

## When this matters

You interact with this layer whenever you:

- Run `attune workflow run` and need a predictable exit code for scripting
- Use `attune costs today` or `attune costs export` to track spend
- Manage cross-session memory with `attune remember` or `attune lessons`
- Inspect routing behaviour with `attune telemetry routing-stats` or `attune telemetry routing-check`
- Configure or verify your setup with `attune doctor` or `attune validate`
