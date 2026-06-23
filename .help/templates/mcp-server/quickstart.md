---
type: quickstart
name: mcp-server-quickstart
feature: mcp-server
depth: quickstart
generated_at: 2026-06-23T22:52:03.357140+00:00
source_hash: 08e50eacebc45c71e34c3de6ca5e70b0eed13373bff884ee18bc5f88124ac95f
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
