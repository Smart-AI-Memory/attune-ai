---
type: quickstart
name: mcp-server-quickstart
feature: mcp-server
depth: quickstart
generated_at: 2026-08-24T13:13:51.843371+00:00
source_hash: e6370b6c61134866408d30c64611640a3ac5184dc9d37f7e676a5f7ad176e69c
status: generated
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
