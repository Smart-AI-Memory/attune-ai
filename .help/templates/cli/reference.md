---
feature: cli
depth: reference
generated_at: 2026-04-06T04:33:24.018601+00:00
source_hash: 60d629c5d9c90360ec0e4d695e0e6548b4a7742f1575ea77863085ed35e3a4ef
status: generated
---

# Cli reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `RoutingPreference` | User's learned routing preferences. | `src/attune/cli_router.py` |
| `HybridRouter` | Routes user input to Claude Code skill invocations. | `src/attune/cli_router.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `get_version()` | Get package version. | `src/attune/cli_minimal.py` |
| `create_parser()` | Create the argument parser. | `src/attune/cli_minimal.py` |
| `main()` | Main entry point. | `src/attune/cli_minimal.py` |
| `route_user_input()` | Quick routing helper. | `src/attune/cli_router.py` |
| `is_slash_command()` | Check if text is a slash command. | `src/attune/cli_router.py` |
| `cmd_costs()` | Show cost report for recent period. | `src/attune/cli_commands/cost_commands.py` |
| `cmd_costs_today()` | Show today's cost summary. | `src/attune/cli_commands/cost_commands.py` |
| `cmd_costs_export()` | Export cost data to file. | `src/attune/cli_commands/cost_commands.py` |
| `cmd_costs_reset()` | Clear all cost tracking data. | `src/attune/cli_commands/cost_commands.py` |
| `cmd_help()` | Handle the `attune help` command. | `src/attune/cli_commands/help_commands.py` |
| `cmd_remember()` | Add a lesson to the lessons file. | `src/attune/cli_commands/memory_commands.py` |
| `cmd_forget()` | Remove a lesson by line number or keyword. | `src/attune/cli_commands/memory_commands.py` |
| `cmd_lessons()` | List current lessons with line numbers. | `src/attune/cli_commands/memory_commands.py` |
| `cmd_provider_show()` | Show current provider configuration. | `src/attune/cli_commands/provider_commands.py` |
| `cmd_provider_set()` | Set the LLM provider. | `src/attune/cli_commands/provider_commands.py` |
| `cmd_telemetry_show()` | Display usage summary. | `src/attune/cli_commands/telemetry_commands.py` |
| `cmd_telemetry_savings()` | Show cost savings from tier routing. | `src/attune/cli_commands/telemetry_commands.py` |
| `cmd_telemetry_export()` | Export telemetry data to file. | `src/attune/cli_commands/telemetry_commands.py` |
| `cmd_telemetry_routing_stats()` | Show adaptive routing statistics. | `src/attune/cli_commands/telemetry_commands.py` |
| `cmd_telemetry_routing_check()` | Check for tier upgrade recommendations. | `src/attune/cli_commands/telemetry_commands.py` |
| `cmd_telemetry_models()` | Show model performance by provider. | `src/attune/cli_commands/telemetry_commands.py` |
| `cmd_telemetry_agents()` | Show active agents and their status. | `src/attune/cli_commands/telemetry_commands.py` |
| `cmd_telemetry_signals()` | Show coordination signals. | `src/attune/cli_commands/telemetry_commands.py` |
| `cmd_setup()` | Install Attune slash commands for Claude Code. | `src/attune/cli_commands/utility_commands.py` |
| `cmd_validate()` | Validate configuration. | `src/attune/cli_commands/utility_commands.py` |
| `cmd_version()` | Show version information. | `src/attune/cli_commands/utility_commands.py` |
| `cmd_features()` | Show available memory and telemetry features. | `src/attune/cli_commands/utility_commands.py` |
| `cmd_doctor()` | Run comprehensive environment health check. | `src/attune/cli_commands/utility_commands.py` |
| `cmd_workflow_list()` | List available workflows. | `src/attune/cli_commands/workflow_commands.py` |
| `cmd_workflow_info()` | Show workflow details. | `src/attune/cli_commands/workflow_commands.py` |
| `cmd_workflow_run()` | Execute a workflow. | `src/attune/cli_commands/workflow_commands.py` |


## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

## Tags

`cli`, `commands`
