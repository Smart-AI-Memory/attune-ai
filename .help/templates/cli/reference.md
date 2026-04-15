---
type: reference
feature: cli
depth: reference
generated_at: 2026-04-14T15:11:07.268587+00:00
source_hash: 8dc008ad217367e499b9e8a37c6cdbb6a23f53f03d344c9793da916a7fb8ab3c
status: generated
---

# CLI reference

## Classes

### RoutingPreference

User's learned routing preferences.

#### Fields

| Field | Type | Default |
|-------|------|---------|
| `keyword` | str | - |
| `skill` | str | - |
| `args` | str | `''` |
| `usage_count` | int | `0` |
| `confidence` | float | `1.0` |

### HybridRouter

Routes user input to Claude Code skill invocations.

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `preferences_path: str \| None = None` | - | Initialize the router |
| `route` | `user_input: str, context: dict[str, Any] \| None = None` | `dict[str, Any]` | Route user input to appropriate skill |
| `learn_preference` | `keyword: str, skill: str, args: str = ''` | `None` | Learn user routing preference |
| `get_suggestions` | `partial: str` | `list[str]` | Get autocomplete suggestions |

## Functions

### Core functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_version` | - | `str` | Get package version |
| `create_parser` | - | `argparse.ArgumentParser` | Create the argument parser |
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

Returns `0` on successful completion.

### Help commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `cmd_help` | `args: argparse.Namespace` | `int` | Handle the `attune help` command |

## Constants

### Help categories

| Constant | Values |
|----------|--------|
| `_CATEGORIES` | `'errors'`, `'warnings'`, `'tips'`, `'references'` |
