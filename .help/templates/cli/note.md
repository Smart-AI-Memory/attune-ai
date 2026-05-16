---
type: note
name: cli-note
feature: cli
depth: note
generated_at: 2026-05-16T06:19:45.831425+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# Note: CLI package structure

## Context

The `cli` feature spans three source locations: `src/attune/cli_minimal.py`, `src/attune/cli_router.py`, and the subpackage `src/attune/cli_commands/`. Together they cover command dispatch, cost tracking, help browsing, routing, and quick-memory lessons.

## Content

The CLI surface combines two kinds of exports: classes in `cli_router.py` and top-level command functions spread across `cli_commands/`.

**Classes (`src/attune/cli_router.py`)**

| Class | Role |
|---|---|
| `RoutingPreference` | Dataclass holding a user's learned keyword-to-skill mapping, with usage count and confidence score. |
| `HybridRouter` | Routes free-form user input to Claude Code skill invocations; learns new preferences via `learn_preference()` and surfaces autocomplete candidates via `get_suggestions()`. |

**Command functions (`src/attune/cli_commands/`)**

| Function | Module | Purpose |
|---|---|---|
| `cmd_costs()` | `cost_commands.py` | Show cost report for a recent period. |
| `cmd_costs_today()` | `cost_commands.py` | Show today's cost summary. |
| `cmd_costs_export()` | `cost_commands.py` | Export cost data to a file. |
| `cmd_costs_reset()` | `cost_commands.py` | Clear all cost tracking data. |
| `cmd_help()` | `help_commands.py` | Handle the `attune help` command. |
| `cmd_remember()` | `memory_commands.py` | Add a lesson to the lessons file. |
| `cmd_forget()` | `memory_commands.py` | Remove a lesson by line number or keyword. |
| `cmd_lessons()` | `memory_commands.py` | List current lessons with line numbers. |
| `cmd_memory_capture()` | `memory_commands.py` | Save content to personal cross-session memory. |
| `cmd_memory_recall()` | `memory_commands.py` | Search personal cross-session memory. |

The classes and functions are designed to compose: `HybridRouter` handles routing decisions, and command functions handle the resulting skill dispatch. `cmd_help()` drives the same template browsing surface described in `help_commands.py`, which exposes 34 filterable tags via `attune help-docs --tags`.

**Tags:** `cli`, `commands`
