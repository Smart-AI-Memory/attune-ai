---
type: faq
name: custom-mcp-stdio-loop-fails-claude-code-handshake
tags: [claude-code]
source: .claude/CLAUDE.md
---

# FAQ: Why does custom MCP stdio loop fails Claude Code handshake?

## Answer

A hand-rolled JSON-RPC `main_loop()` reading `sys.stdin` line by line does not implement the MCP initialization sequence (capability negotiation, `initialize` method). Claude Code's MCP client expects the standard protocol and silently drops the connection.

**How to fix:**
- use the official `mcp.server.Server` + `mcp.server.stdio.stdio_server` which handles the full handshake

```
main_loop()
```

## Related Topics
- **Error**: Detailed error: Custom MCP stdio loop fails Claude Code handshake
