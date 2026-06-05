---
type: reference
name: cli-reference
feature: cli
depth: reference
generated_at: 2026-06-04T23:39:47.643616+00:00
source_hash: 4b177dd28a8ce19bb06606b9ae39e4fe255d7f2fe854f3376d3330f151f3ffac
status: generated
---

# CLI reference

Use this reference to look up the command handlers, routing utilities, entry point, and data types that make up the attune command-line interface.

## Classes

| Class | Description | File |
|-------|-------------|------|
| `RoutingPreference` | User's learned routing preference for a keyword. | `src/attune/cli_router.py` |
| `HybridRouter` | Routes user input to Claude Code skill invocations. | `src/attune/cli_router.py` |

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
| `__init__` | `preferences_path: str | None = None` | — | Initialize the router, optionally loading preferences from a file path. |
| `route` | `user_input: str, context: dict[str, Any] | None = None` | `dict[str, Any]` | Route user input to a skill invocation. |
| `learn_preference` | `keyword: str, skill: str, args: str = ''` | — | Record a keyword-to-skill mapping as a learned preference. |
| `get_suggestions` | `partial: str` | `list[str]` | Return completions for a partial keyword string. |

## Functions

### Entry point

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_version` | — | `str` | Return the installed package version. |
| `create_parser` | — | `argparse.ArgumentParser` | Build and return the top-level argument parser. |
| `main` | `argv: list[str] | None = None` | `int` | CLI entry point; parses `argv` and dispatches to the appropriate command handler. |

### Routing

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `route_user_input` | `user_input: str, context: dict[str, Any] | None = None` | `dict[str, Any]` | Route a user input string to a skill invocation and return the result dict. |
| `is_slash_command` | `text: str` | `bool` | Return `True` if `text` begins with a slash command prefix. |

### Workflow execution

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `run_workflow_with_exit_code` | `workflow_cls: type, input_data: dict[str, Any], *, name: str, json_mode: bool, print_result: Callable[[Any], None]` | `int` | Instantiate and execute a workflow, then return the contract exit code. |

### Cost commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_costs` | `args: Namespace` | `int` | Show cost report for recent period. |
| `cmd_costs_today` | `args: Namespace` | `int` | Show today's cost summary. |
| `cmd_costs_export` | `args: Namespace` | `int` | Export cost data to file. |
| `cmd_costs_reset` | `args: Namespace` | `int` | Clear all cost tracking data. |

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

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

## Tags

`cli`, `commands`
