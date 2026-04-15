---
type: faq
feature: mcp-server
depth: faq
generated_at: 2026-04-14T15:00:49.309863+00:00
source_hash: bcc1c0a657ed14e3ecc0ddf2aa190500d4decf1e455d572148863bce6b9d9c27
status: generated
---

# Mcp Server FAQ

## What is the MCP server?

The Attune AI MCP server that provides tools for workflows, authentication, memory, and contextual help through the Model Context Protocol.

## When should I use the MCP server?

Use the MCP server when you need to connect Attune AI workflows to an MCP-compatible client like Claude Desktop. It exposes all Attune tools, prompts, and resources through the standard MCP protocol.

## How do I start the server?

Run `python -m attune.mcp.server` or call the `main()` function. You can also create a server instance directly with `create_server()`.

## What tools does the server provide?

The server provides four categories of tools:

- **Workflow tools**: Execute Attune AI workflows
- **Utility tools**: Authentication status, telemetry stats, and session management
- **Help tools**: Contextual documentation and progressive help lookup
- **Memory tools**: Store, retrieve, search, and forget data across sessions

## How does rate limiting work?

The `RateLimiter` class uses a sliding window approach with a default limit of 60 calls per 60 seconds. You can customize these values when creating a server instance.

## What prompts are available?

The server exposes three built-in prompts:

- `security-scan`: Comprehensive security analysis for directories
- `test-gen`: Generate behavioral tests for Python modules
- `cost-report`: Cost optimization analysis with cache hit rates

## How do I debug server issues?

First check that your MCP client is properly configured to connect to the server. Enable debug logging to see tool calls and responses. The server handles errors gracefully and returns structured error messages through the MCP protocol.

## Where are the source files?

- `src/attune/mcp/server.py` - Main server implementation
- `src/attune/mcp/memory.py` - Memory tool handlers
- `src/attune/mcp/prompts.py` - Prompt handling
- `src/attune/mcp/rate_limit.py` - Rate limiting

**Tags:** `mcp`, `tools`, `server`
