---
type: reference
name: cli-reference
feature: cli
depth: reference
generated_at: 2026-05-16T06:19:45.808782+00:00
source_hash: 8c67b256a4817afea8eb428fdd577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# CLI reference

Use this reference to invoke attune's command-line interface, configure routing, and manage memory, costs, telemetry, and workflows from the terminal.

## Classes

| Class | Description |
|-------|-------------|
| `RoutingPreference` | User's learned routing preferences. |
| `HybridRouter` | Routes user input to Claude Code skill invocations. |

### `RoutingPreference` fields

`RoutingPreference` is a dataclass.

| Field | Type | Default |
|-------|------|---------|
| `keyword` | `str` | — |
| `skill` | `str` | — |
| `args` | `str` | `''` |
| `usage_count` | `int` | `0` |
| `confidence` | `float` | `1.0` |

### `HybridRouter` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `preferences_path: str \| None = None` | — | Initializes the router, optionally loading preferences from a file path. |
| `route` | `user_input: str, context: dict[str, Any] \| None = None` | `dict[str, Any]` | Routes user input to a Claude Code skill invocation. |
| `learn_preference` | `keyword: str, skill: str, args: str = ''` | `None` | Records a routing preference for a keyword–skill pair. |
| `get_suggestions` | `partial: str` | `list[str]` | Returns skill suggestions matching a partial input string. |

## Functions

### Cost commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_costs` | `args: Namespace` | `int` | Show cost report for recent period. |
| `cmd_costs_today` | `args: Namespace` | `int` | Show today's cost summary. |
| `cmd_costs_export` | `args: Namespace` | `int` | Export cost data to file. |
| `cmd_costs_reset` | `args: Namespace` | `int` | Clear all cost tracking data. Always returns `0`. |

### Help commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_help` | `args: argparse.Namespace` | `int` | Handle the `attune help` command. |

### Memory commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_remember` | `args: Namespace` | `int` | Add a lesson to the lessons file. |
| `cmd_forget` | `args: Namespace` | `int` | Remove a lesson by line number or keyword. |
| `cmd_lessons` | `args: Namespace` | `int` | List current lessons with line numbers. |
| `cmd_memory_capture` | `args: Namespace` | `int` | Save content to personal cross-session memory. |
| `cmd_memory_recall` | `args: Namespace` | `int` | Search personal cross-session memory. |
| `cmd_memory_topics` | `args: Namespace` | `int` | List all personal memory topics. |
| `cmd_memory_forget_topic` | `args: Namespace` | `int` | Delete a topic (or specific kind) from personal memory. |

### Provider commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_provider_show` | `args: Namespace` | `int` | Show current provider configuration. |
| `cmd_provider_set` | `args: Namespace` | `int` | Set the LLM provider. |

### Telemetry commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_telemetry_show` | `args: Namespace` | `int` | Display usage summary. |
| `cmd_telemetry_savings` | `args: Namespace` | `int` | Show cost savings from tier routing. |
| `cmd_telemetry_export` | `args: Namespace` | `int` | Export telemetry data to file. |
| `cmd_telemetry_routing_stats` | `args: Namespace` | `int` | Show adaptive routing statistics. |
| `cmd_telemetry_routing_check` | `args: Namespace` | `int` | Check for tier upgrade recommendations. |
| `cmd_telemetry_models` | `args: Namespace` | `int` | Show model performance by provider. |
| `cmd_telemetry_agents` | `args: Namespace` | `int` | Show active agents and their status. |
| `cmd_telemetry_signals` | `args: Namespace` | `int` | Show coordination signals. |

### Utility commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_setup` | `args: Namespace` | `int` | Install Attune slash commands for Claude Code. |
| `cmd_validate` | `args: Namespace` | `int` | Validate configuration. |
| `cmd_version` | `args: Namespace` | `int` | Show version information. |
| `cmd_features` | `args: Namespace` | `int` | Show available memory and telemetry features. |
| `cmd_doctor` | `args: Namespace` | `int` | Run comprehensive environment health check. |

### Workflow commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_workflow_list` | `args: Namespace` | `int` | List available workflows. |
| `cmd_workflow_info` | `args: Namespace` | `int` | Show workflow details. |
| `cmd_workflow_run` | `args: Namespace` | `int` | Execute a workflow. |

### Entry point and routing helpers

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_version` | — | `str` | Get package version. |
| `create_parser` | — | `argparse.ArgumentParser` | Create the argument parser. |
| `main` | `argv: list[str] \| None = None` | `int` | Main entry point. |
| `route_user_input` | `user_input: str, context: dict[str, Any] \| None = None` | `dict[str, Any]` | Quick routing helper. |
| `is_slash_command` | `text: str` | `bool` | Check if text is a slash command. |

## Constants

### Cost command exports

| Constant | Members |
|----------|---------|
| `__all__` | `'cmd_costs'`, `'cmd_costs_export'`, `'cmd_costs_reset'`, `'cmd_costs_today'` |

### Memory command exports

| Constant | Members |
|----------|---------|
| `__all__` | `'cmd_forget'`, `'cmd_lessons'`, `'cmd_memory_capture'`, `'cmd_memory_forget_topic'`, `'cmd_memory_recall'`, `'cmd_memory_topics'`, `'cmd_remember'` |

### Help command categories

| Constant | Members |
|----------|---------|
| `_CATEGORIES` | `'errors'`, `'warnings'`, `'tips'`, `'references'` |

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

## Tags

`cli`, `commands`
