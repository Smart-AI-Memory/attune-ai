---
feature: cli
depth: reference
generated_at: 2026-04-13T16:59:49.927429+00:00
source_hash: 8dc008ad217367e499b9e8a37c6cdbb6a23f53f03d344c9793da916a7fb8ab3c
status: generated
---

# CLI reference

The Attune AI CLI provides a hybrid command interface that routes user input between structured commands and natural language processing through Claude Code skills.

## Classes

| Class | Description | File |
|-------|-------------|------|
| `RoutingPreference` | Stores user's learned routing preferences for command interpretation. | `src/attune/cli_router.py` |
| `HybridRouter` | Routes user input between traditional CLI commands and Claude Code skill invocations. | `src/attune/cli_router.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `get_version()` | Retrieves the current package version string. | `src/attune/cli_minimal.py` |
| `create_parser()` | Creates and configures the argument parser for CLI commands. | `src/attune/cli_minimal.py` |
| `main()` | Primary entry point that initializes the CLI and processes user input. | `src/attune/cli_minimal.py` |
| `route_user_input()` | Determines whether input should be handled as a command or natural language. | `src/attune/cli_router.py` |
| `is_slash_command()` | Identifies if input text begins with a slash command prefix. | `src/attune/cli_router.py` |
| `cmd_costs()` | Displays cost report for a specified recent time period. | `src/attune/cli_commands/cost_commands.py` |
| `cmd_costs_today()` | Shows a summary of today's usage costs. | `src/attune/cli_commands/cost_commands.py` |
| `cmd_costs_export()` | Exports cost tracking data to a specified file format. | `src/attune/cli_commands/cost_commands.py` |
| `cmd_costs_reset()` | Removes all stored cost tracking data from the system. | `src/attune/cli_commands/cost_commands.py` |
| `cmd_help()` | Processes help requests and displays documentation templates. | `src/attune/cli_commands/help_commands.py` |
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
