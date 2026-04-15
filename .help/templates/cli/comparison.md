---
type: comparison
feature: cli
depth: comparison
generated_at: 2026-04-14T15:12:47.499119+00:00
source_hash: 8dc008ad217367e499b9e8a37c6cdbb6a23f53f03d344c9793da916a7fb8ab3c
status: generated
---

# CLI command interface vs direct API calls

## Overview

Attune offers two ways to interact with its functionality: through the hybrid CLI that combines slash commands with natural language routing, or by calling the underlying API functions directly in your code.

## Feature comparison

| Aspect | CLI Interface | Direct API Calls |
|--------|---------------|------------------|
| **Input style** | Natural language + slash commands | Function calls with typed parameters |
| **Routing** | Automatic via `HybridRouter` with learning | Manual function selection |
| **Cost tracking** | Built-in commands (`costs`, `costs-today`, `costs-export`) | Requires separate implementation |
| **Help system** | Interactive help with `cmd_help()` | Documentation lookup only |
| **Learning** | Adapts routing preferences over time | Static behavior |
| **Error handling** | Standardized CLI error codes | Custom exception handling |
| **Batch operations** | Command chaining and scripting | Programmatic loops and conditions |

## Use the CLI when

- **You want natural language interaction**: The hybrid router lets you type "show me today's costs" instead of memorizing command syntax
- **You need cost visibility**: Built-in cost tracking commands provide immediate usage insights without additional setup
- **You're doing exploratory work**: The learning router adapts to your patterns, making repeated tasks faster over time
- **You prefer command-line workflows**: Integrates naturally with shell scripts and terminal-based development

Key entry points:
- `main()` — Primary CLI entry point with full argument parsing
- `route_user_input()` — Direct access to the hybrid routing system
- `cmd_costs_*()` functions — Comprehensive cost analysis tools

## Use direct API calls when

- **You're building applications**: Direct function calls offer better error handling and type safety for programmatic use
- **You need precise control**: Bypass the routing layer when you know exactly which functions to call
- **You're writing libraries**: Other developers expect function APIs, not CLI subprocess calls
- **Performance is critical**: Direct calls avoid the parsing and routing overhead (~10-20ms per command)

## Recommendation

**Start with the CLI** for most use cases. The hybrid router's natural language processing and automatic learning make it significantly more usable than traditional command-line tools. The cost tracking and help systems are mature and immediately useful.

**Switch to direct API calls** only when you need the CLI's functionality embedded in larger applications or when you're building tools for other developers to consume programmatically.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

**Tags:** `cli`, `commands`
