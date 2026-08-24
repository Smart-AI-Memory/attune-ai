---
name: mcp-server
source: content/features/mcp-server.md
tags:
- mcp
- tools
- server
type: tip
---

# The Model Context Protocol server that exposes attune workflows, help, and memory as tools

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  `create_server` and `AttuneMCPServer` from `attune.mcp`; the
  tool-schema group functions live in `attune.mcp.tool_schemas`.
  Handler methods and the dispatch table are internal.
- **`await` `call_tool`.** It's the one async entry; the inspection
  helpers are sync.
- **Read the log file to debug.** stdout is reserved for the protocol.
- **Tool contracts live with their features.** This page covers the
  server; each tool's inputs are documented on its own feature page.
