---
name: cli
source: content/features/cli.md
tags:
- cli
- commands
type: comparison
---

# The attune command-line interface and its natural-language router

## Comparison

The CLI is one of three front doors to attune:

| | CLI (`attune`) | MCP server | ops dashboard |
|--|----------------|------------|---------------|
| Surface | terminal subcommands | tools in a conversation | local web UI |
| Entry | `attune <command>` | `python -m attune.mcp.server` | `python -m attune.ops` |
| Best for | scripting, terminal use | Claude Code workflows | visual runs/metrics |

The CLI and the MCP server expose overlapping capabilities (run a
workflow, read telemetry) through different surfaces; the router lets
the CLI accept natural language as well as explicit subcommands.
