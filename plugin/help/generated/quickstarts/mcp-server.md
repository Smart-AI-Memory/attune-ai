---
name: mcp-server
source: content/features/mcp-server.md
tags:
- mcp
- tools
- server
type: quickstart
---

# The Model Context Protocol server that exposes attune workflows, help, and memory as tools

## Quickstart

Register the server with Claude Code via `.mcp.json` (the plugin ships
this) so the tools appear in your conversation:

```json
{
  "mcpServers": {
    "attune-ai": {
      "command": "uv",
      "args": ["run", "python", "-m", "attune.mcp.server"]
    }
  }
}
```

Once connected, the built-in tools (`code_review`, `help_lookup`,
`memory_store`, …) — plus any registered by installed plugins — are
callable from the conversation. To run the server directly for testing:

```bash
python -m attune.mcp.server
```
