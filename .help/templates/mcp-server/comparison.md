---
type: comparison
name: mcp-server-comparison
feature: mcp-server
depth: comparison
generated_at: 2026-08-24T13:13:51.843371+00:00
source_hash: e6370b6c61134866408d30c64611640a3ac5184dc9d37f7e676a5f7ad176e69c
status: generated
---

# The Model Context Protocol server that exposes attune workflows, help, and memory as tools

## Comparison

The MCP server is the **delivery surface** for attune's tools, not a
workflow itself:

| | mcp-server | A workflow (e.g. security-audit) | ops-dashboard |
|--|-----------|----------------------------------|---------------|
| Role | Exposes tools/resources/prompts to an MCP client | One analysis the server can run | Local web UI for running workflows |
| Transport | MCP over stdio | n/a (invoked via a tool/CLI) | HTTP |
| Entry | `python -m attune.mcp.server` + `.mcp.json` | `attune workflow run <slug>` / its MCP tool | `python -m attune.ops` |

The server is how the *conversational* surface reaches every feature;
the CLI (`attune workflow run`) and the ops dashboard are the other two
front doors.
