---
type: comparison
feature: mcp-server
depth: comparison
generated_at: 2026-04-20T01:22:25.202233+00:00
source_hash: cab70f0aeb1782a9a9523b0ae9f7a4efe73904a1e5f3f26ec70fc1f9dc7cd315
status: generated
---

# MCP Server vs direct API calls

The Attune AI MCP Server provides a structured interface for Claude Code and other MCP clients to access workflows, help, memory, and authentication tools. You can also call these capabilities directly through Python imports, but each approach has distinct tradeoffs.

## Feature comparison

| Aspect | MCP Server | Direct API calls |
|--------|------------|------------------|
| **Client support** | Any MCP-compatible client (Claude Code, others) | Python code only |
| **Setup overhead** | Requires `.mcp.json` configuration | Import statements |
| **Rate limiting** | Built-in sliding window (60 calls/min) | Manual implementation needed |
| **Tool discovery** | Automatic via `get_tool_list()` | Must know function signatures |
| **Authentication** | Handled by server instance | Manual credential management |
| **Error handling** | Standardized MCP error responses | Raw Python exceptions |
| **Session state** | Persistent across tool calls | Manual state management |
| **Progress feedback** | Structured status updates | Print statements or logging |

## Performance characteristics

**MCP Server** adds ~50ms overhead per tool call due to JSON serialization and protocol handling, but provides automatic caching for prompts and tool definitions. The rate limiter prevents runaway API costs.

**Direct API calls** have minimal overhead (~5ms) but require you to implement your own caching, rate limiting, and error recovery. For batch operations processing hundreds of files, direct calls can be 10x faster.

## Use MCP Server when...

- Working in Claude Code or other MCP clients
- You need the help system (`help_lookup`, `help_maintain`)
- Building interactive workflows that benefit from session state
- Rate limiting and cost protection are important
- You want standardized error handling across tools

## Use direct API calls when...

- Writing Python scripts or applications
- Performance is critical (batch processing, CLI tools)
- You need capabilities not exposed through MCP tools
- Building automation that runs without human interaction
- You're already managing authentication and state elsewhere

## Getting started

**MCP Server**: Create `.mcp.json` in your project root with `uv run python -m attune.mcp.server` as the command. Test with `ps aux | grep attune` to verify it's running.

**Direct API**: Import from `attune.workflows`, `attune.auth`, or `attune.help` modules. Check the reference documentation for specific function signatures.
