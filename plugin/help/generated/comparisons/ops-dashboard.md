---
name: ops-dashboard
source: content/features/ops-dashboard.md
tags:
- ops
- dashboard
- runner
- workflows
- scope-picker
- persistence
- sse
type: comparison
---

# The local FastAPI operations dashboard — a workflow runner with per-feature scope, persisted run history, workflow chaining, and live SSE log streaming

## Comparison

The ops dashboard is one of three front doors to attune's workflows:

| | ops-dashboard | mcp-server | CLI |
|--|---------------|-----------|-----|
| Surface | Local web UI (HTTP) | MCP tools (stdio) | `attune workflow run` |
| Strength | Scope picker, run history, chaining, live SSE | In-conversation tool calls | Scriptable one-shots |
| Entry | `attune ops` | `python -m attune.mcp.server` | `attune workflow run <slug>` |

It is the *browser* front door; the MCP server is the *conversational*
one; the CLI is the *terminal* one. The dashboard renders cost,
telemetry, and help data those other features own.
