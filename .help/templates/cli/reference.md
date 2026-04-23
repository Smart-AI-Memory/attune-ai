---
type: reference
feature: cli
depth: reference
generated_at: 2026-04-23T03:32:11.954475+00:00
source_hash: 95afb1e38daa117bab7e14bf58b614da535d484b24b1dd072c4750e232202196
status: generated
---

# CLI reference

Access Attune AI's hybrid command-line interface that routes input between skills and natural language processing.

## Classes

| Class | Description |
|-------|-------------|
| `RoutingPreference` | User's learned routing preferences |
| `HybridRouter` | Routes user input to Claude Code skill invocations |

### RoutingPreference fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `keyword` | str | | Command keyword |
| `skill` | str | | Target skill name |
| `args` | str | `''` | Skill arguments |
| `usage_count` | int | `0` | Number of times used |
| `confidence` | float | `1.0` | Routing confidence score |

### HybridRouter methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `preferences_path: str \| None = None` | | Initialize router with optional preferences file |
| `route` | `user_input: str, context: dict[str, Any] \| None = None` | `dict[str, Any]` | Route user input to skill invocation |
| `learn_preference` | `keyword: str, skill: str, args: str = ''` | None | Learn new routing preference |
| `get_suggestions` | `partial: str` | `list[str]` | Get command suggestions for partial input |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_version` | | `str` | Get package version |
| `create_parser` | | `argparse.ArgumentParser` | Create the argument parser |
| `main` | `argv: list[str] \| None = None` | `int` | Main entry point |
| `route_user_input` | `user_input: str, context: dict[str, Any] \| None = None` | `dict[str, Any]` | Quick routing helper |
| `is_slash_command` | `text: str` | `bool` | Check if text is a slash command |

### Cost commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_costs` | `args: Namespace` | `int` | Show cost report for recent period |
| `cmd_costs_today` | `args: Namespace` | `int` | Show today's cost summary |
| `cmd_costs_export` | `args: Namespace` | `int` | Export cost data to file |
| `cmd_costs_reset` | `args: Namespace` | `int` | Clear all cost tracking data |

#### cmd_costs_reset returns

```
0
```

### Help commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_help` | `args: argparse.Namespace` | `int` | Handle the `attune help` command |

### Memory commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_remember` | | | Add a lesson to the lessons file |
| `cmd_forget` | | | Remove a lesson by line number or keyword |
| `cmd_lessons` | | | List current lessons with line numbers |
| `cmd_memory_capture` | | | Save content to personal cross-session memory |
| `cmd_memory_recall` | | | Search personal cross-session memory |
| `cmd_memory_topics` | | | List all personal memory topics |
| `cmd_memory_forget_topic` | | | Delete a topic from personal memory |

### Provider commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_provider_show` | | | Show current provider configuration |
| `cmd_provider_set` | | | Set the LLM provider |

### Telemetry commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_telemetry_show` | | | Display usage summary |
| `cmd_telemetry_savings` | | | Show cost savings from tier routing |
| `cmd_telemetry_export` | | | Export telemetry data to file |
| `cmd_telemetry_routing_stats` | | | Show adaptive routing statistics |
| `cmd_telemetry_routing_check` | | | Check for tier upgrade recommendations |
| `cmd_telemetry_models` | | | Show model performance by provider |
| `cmd_telemetry_agents` | | | Show active agents and their status |
| `cmd_telemetry_signals` | | | Show coordination signals |

### Utility commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_setup` | | | Install Attune slash commands for Claude Code |
| `cmd_validate` | | | Validate configuration |
| `cmd_version` | | | Show version information |
| `cmd_features` | | | Show available memory and telemetry features |
| `cmd_doctor` | | | Run comprehensive environment health check |

### Workflow commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_workflow_list` | | | List available workflows |
| `cmd_workflow_info` | | | Show workflow details |
| `cmd_workflow_run` | | | Execute a workflow |

## Constants

| Constant | Values |
|----------|--------|
| `_CATEGORIES` | `errors`, `warnings`, `tips`, `references` |
