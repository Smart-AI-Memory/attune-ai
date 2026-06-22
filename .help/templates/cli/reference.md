---
type: reference
name: cli-reference
feature: cli
depth: reference
generated_at: 2026-06-22T09:48:39.757537+00:00
source_hash: 164b677043cfbe05cdc85850c811ec14af92dabac3c48dced21fedf0c3c58146
status: generated
---

# CLI reference

Use these modules to invoke attune commands, route user input to Claude Code skills, and integrate attune workflows into scripts with predictable exit codes.

## Classes

| Class | Description |
|-------|-------------|
| `RoutingPreference` | Learned routing preference that maps a keyword to a skill invocation. |
| `HybridRouter` | Routes user input to Claude Code skill invocations, learning from recorded preferences. |

### `RoutingPreference` fields

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
| `__init__` | `preferences_path: str | None = None` | — | Initialize the router, optionally loading preferences from a file. |
| `route` | `user_input: str, context: dict[str, Any] | None = None` | `dict[str, Any]` | Route user input to a skill invocation. |
| `learn_preference` | `keyword: str, skill: str, args: str = ''` | `None` | Record a keyword-to-skill mapping for future routing. |
| `get_suggestions` | `partial: str` | `list[str]` | Return skill suggestions matching a partial input string. |

## Functions

### Entry point

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main` | `argv: list[str] | None = None` | `int` | Main entry point for the `attune` command. |
| `create_parser` | — | `argparse.ArgumentParser` | Build the argument parser for the `attune` CLI. |
| `get_version` | — | `str` | Return the installed package version. |

### Routing

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `route_user_input` | `user_input: str, context: dict[str, Any] | None = None` | `dict[str, Any]` | Route a user input string to a skill invocation without constructing a `HybridRouter`. |
| `is_slash_command` | `text: str` | `bool` | Return `True` if `text` begins with a slash command. |

### Workflow execution

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `run_workflow_with_exit_code` | `workflow_cls: type, input_data: dict[str, Any], *, name: str, json_mode: bool, print_result: Callable[[Any], None], on_result: Callable[[Any], None] | None = None` | `int` | Instantiate and execute a workflow, returning the contract exit code. |
| `cmd_workflow_list` | `args: Namespace` | `int` | List available workflows. |
| `cmd_workflow_info` | `args: Namespace` | `int` | Show workflow details. |
| `cmd_workflow_run` | `args: Namespace` | `int` | Execute a workflow. |

### Cost tracking

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_costs` | `args: Namespace` | `int` | Show cost report for recent period. |
| `cmd_costs_today` | `args: Namespace` | `int` | Show today's cost summary. |
| `cmd_costs_export` | `args: Namespace` | `int` | Export cost data to file. |
| `cmd_costs_reset` | `args: Namespace` | `int` | Clear all cost tracking data. |

### Memory

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_memory_agent` | `args: Any` | `int` | Run a single-shot agent with attune's Redis-backed Memory tool. |
| `cmd_remember` | `args: Namespace` | `int` | Add a lesson to the lessons file. |
| `cmd_forget` | `args: Namespace` | `int` | Remove a lesson by line number or keyword. |
| `cmd_lessons` | `args: Namespace` | `int` | List current lessons with line numbers. |
| `cmd_memory_capture` | `args: Namespace` | `int` | Save content to personal cross-session memory. |
| `cmd_memory_recall` | `args: Namespace` | `int` | Search personal cross-session memory. |
| `cmd_memory_topics` | `args: Namespace` | `int` | List all personal memory topics. |
| `cmd_memory_forget_topic` | `args: Namespace` | `int` | Delete a topic (or specific kind) from personal memory. |

### Pattern review

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_patterns_review` | `args: Any` | `int` | List staged patterns awaiting review. |
| `cmd_patterns_promote` | `args: Any` | `int` | Promote a staged pattern into the active library. |
| `cmd_patterns_reject` | `args: Any` | `int` | Reject (drop) a staged pattern. |

### Provider configuration

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_provider_show` | `args: Namespace` | `int` | Show current provider configuration. |
| `cmd_provider_set` | `args: Namespace` | `int` | Set the LLM provider. |

### Telemetry

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

### Utility

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_setup` | `args: Namespace` | `int` | Install Attune slash commands for Claude Code. |
| `cmd_validate` | `args: Namespace` | `int` | Validate configuration. |
| `cmd_version` | `args: Namespace` | `int` | Show version information. |
| `cmd_features` | `args: Namespace` | `int` | Show available memory and telemetry features. |
| `cmd_doctor` | `args: Namespace` | `int` | Run comprehensive environment health check. |
| `cmd_help` | `args: argparse.Namespace` | `int` | Handle the `attune help` command. |
| `cmd_curator` | `args: Any` | `int` | Render the curator briefing for the current project. |

## Module constants

| Constant | Type | Members |
|----------|------|---------|
| `_CATEGORIES` | `tuple` | `'errors'`, `'warnings'`, `'tips'`, `'references'` |
| `_DEFAULT_MODEL` | `str` | `'claude-sonnet-4-6'` |
| `_MEMORY_BETA` | `str` | `'context-management-2025-06-27'` |

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

## Tags

`cli`, `commands`
