---
type: reference
feature: cli
depth: reference
generated_at: 2026-05-04T02:34:16.611938+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# CLI reference

Execute Attune commands from the terminal, manage costs, store lessons, and configure providers.

## RoutingPreference dataclass

User's learned routing preferences.

| Field | Type | Default |
|-------|------|---------|
| `keyword` | `str` | |
| `skill` | `str` | |
| `args` | `str` | `''` |
| `usage_count` | `int` | `0` |
| `confidence` | `float` | `1.0` |

## HybridRouter class

Routes user input to Claude Code skill invocations.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `preferences_path: str \| None = None` | | Initialize router with optional preferences file |
| `route` | `user_input: str, context: dict[str, Any] \| None = None` | `dict[str, Any]` | Route input to appropriate skill |
| `learn_preference` | `keyword: str, skill: str, args: str = ''` | `None` | Store routing preference for future use |
| `get_suggestions` | `partial: str` | `list[str]` | Get command suggestions for partial input |

## Cost tracking functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_costs` | `args: Namespace` | `int` | Show cost report for recent period |
| `cmd_costs_today` | `args: Namespace` | `int` | Show today's cost summary |
| `cmd_costs_export` | `args: Namespace` | `int` | Export cost data to file |
| `cmd_costs_reset` | `args: Namespace` | `int` | Clear all cost tracking data |

## Help functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_help` | `args: argparse.Namespace` | `int` | Handle the `attune help` command |

## Memory functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_remember` | `args: Namespace` | `int` | Add a lesson to the lessons file |
| `cmd_forget` | `args: Namespace` | `int` | Remove a lesson by line number or keyword |
| `cmd_lessons` | `args: Namespace` | `int` | List current lessons with line numbers |
| `cmd_memory_capture` | `args: Namespace` | `int` | Save content to personal cross-session memory |
| `cmd_memory_recall` | `args: Namespace` | `int` | Search personal cross-session memory |

## Routing utilities

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `route_user_input` | | | Quick routing helper |
| `is_slash_command` | | | Check if text is a slash command |

## Core CLI functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_version` | | | Get package version |
| `create_parser` | | | Create the argument parser |
| `main` | | | Main entry point |

## Constants

| Constant | Values |
|----------|--------|
| `_CATEGORIES` | `'errors'`, `'warnings'`, `'tips'`, `'references'` |
