---
type: comparison
name: cli-comparison
feature: cli
depth: comparison
generated_at: 2026-06-24T04:24:53.876139+00:00
source_hash: bd2a2253f6a68a6b8671e90b653a8b827a19319e732c7538d504fb7c9e90bdb4
status: generated
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
