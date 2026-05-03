---
name: custom-mcp-stdio-loop-fails-claude-code-handshake
source: .claude/CLAUDE.md
summary: This developer help template explains why custom JSON-RPC stdio loops fail
  to connect with Claude Code's MCP client and demonstrates how to use the official
  MCP server components to properly implement the required initialization handshake
  and capability negotiation.
tags:
- claude-code
type: faq
---

# FAQ: Why Does a Custom MCP stdio Loop Fail the Claude Code Handshake?

## Answer

A hand-rolled JSON-RPC `main_loop()` that reads `sys.stdin` line by line does not implement the MCP initialization sequence, which includes capability negotiation and the `initialize` method. Claude Code's MCP client expects this standard protocol handshake and will silently drop connections that don't conform to it.

**How to fix:**

Replace your custom loop with the official MCP server components, which handle the full handshake automatically:

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server

# The official server handles capability negotiation and the initialize handshake
app = Server("your-server-name")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())
```

Using `mcp.server.Server` together with `mcp.server.stdio.stdio_server` ensures that:

- The `initialize` request and response are handled correctly
- Capability negotiation completes before any tool or resource calls are made
- The connection is not silently dropped by the Claude Code MCP client

## Related Topics

- **Error reference**: [Custom MCP stdio loop fails Claude Code handshake](./errors/mcp-stdio-handshake-failure.md)
