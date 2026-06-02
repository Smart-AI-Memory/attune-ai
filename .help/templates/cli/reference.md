---
type: reference
name: cli-reference
feature: cli
depth: reference
generated_at: 2026-06-02T10:56:02.712869+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# CLI reference

Use this reference to look up every command handler, routing function, parser entry point, and data class in the attune command-line interface.

## Classes

### `RoutingPreference`

`attune.cli_router` — `[dataclass]` — Stores a user's learned routing preference for a keyword.

| Field | Type | Default |
|-------|------|---------|
| `keyword` | `str` | — |
| `skill` | `str` | — |
| `args` | `str` | `''` |
| `usage_count` | `int` | `0` |
| `confidence` | `float` | `1.0` |

### `HybridRouter`

`attune.cli_router` — Routes user input to Claude Code skill invocations.

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `preferences_path: str \| None = None` | — | Initialize the router, optionally loading preferences from a file path. |
| `route` | `user_input: str, context: dict[str, Any] \| None = None` | `dict[str, Any]` | Route user input to a skill, returning a routing result dict. |
| `learn_preference` | `keyword: str, skill: str, args: str = ''` | — | Record a keyword-to-skill mapping to improve future routing. |
| `get_suggestions` | `partial: str` | `list[str]` | Return autocomplete suggestions for a partial input string. |

## Functions

### Entry point

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | `argv: list[str] \| None = None` | `int` | CLI entry point; parses `argv` (or `sys.argv`) and dispatches to the appropriate command handler. |
| `create_parser` | — | `argparse.ArgumentParser` | Build and return the top-level argument parser. |
| `get_version` | — | `str` | Return the installed package version string. |

### Routing

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `route_user_input` | `user_input: str, context: dict[str, Any] \| None = None` | `dict[str, Any]` | Quick routing helper; resolve user input to a skill invocation dict without instantiating `HybridRouter` directly. |
| `is_slash_command` | `text: str` | `bool` | Return `True` if `text` is a slash command. |

### Cost commands

`cli_commands.cost_commands`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_costs` | `args: Namespace` | `int` | Show cost report for recent period. |
| `cmd_costs_today` | `args: Namespace` | `int` | Show today's cost summary. |
| `cmd_costs_export` | `args: Namespace` | `int` | Export cost data to file. |
| `cmd_costs_reset` | `args: Namespace` | `int` | Clear all cost tracking data. |

### Help commands

`cli_commands.help_commands`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_help` | `args: argparse.Namespace` | `int` | Handle the `attune help` command. |

### Memory commands

`cli_commands.memory_commands`

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

`cli_commands.provider_commands`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_provider_show` | `args: Namespace` | `int` | Show current provider configuration. |
| `cmd_provider_set` | `args: Namespace` | `int` | Set the LLM provider. |

### Telemetry commands

`cli_commands.telemetry_commands`

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

`cli_commands.utility_commands`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_setup` | `args: Namespace` | `int` | Install Attune slash commands for Claude Code. |
| `cmd_validate` | `args: Namespace` | `int` | Validate configuration. |
| `cmd_version` | `args: Namespace` | `int` | Show version information. |
| `cmd_features` | `args: Namespace` | `int` | Show available memory and telemetry features. |
| `cmd_doctor` | `args: Namespace` | `int` | Run comprehensive environment health check. |

### Workflow commands

`cli_commands.workflow_commands`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_workflow_list` | `args: Namespace` | `int` | List available workflows. |
| `cmd_workflow_info` | `args: Namespace` | `int` | Show workflow details. |
| `cmd_workflow_run` | `args: Namespace` | `int` | Execute a workflow. |

## Constants

### `_CATEGORIES`

Members used to filter help template listings.

| Constant | Type | Values |
|----------|------|--------|
| `_CATEGORIES` | `tuple` | `'errors'`, `'warnings'`, `'tips'`, `'references'` |

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

## Tags

`cli`, `commands`
