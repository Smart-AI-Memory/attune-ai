---
type: comparison
feature: mcp-server
depth: comparison
generated_at: 2026-04-19T18:50:02.013693+00:00
source_hash: 4d53983ae8928abce86e5e58e1d186acd20ca65e85b505d31acc051216daed33
status: generated
---

# Comparison: Direct Python API vs MCP server

## Feature comparison

| Feature | Direct Python imports | MCP server |
|---|---|---|
| **Setup complexity** | Import attune-ai package | Configure `.mcp.json` + Claude Code |
| **Tool access** | All internal APIs available | 15 exposed tools via MCP protocol |
| **Rate limiting** | Manual implementation | Built-in 60 calls/minute sliding window |
| **Claude integration** | Manual prompt construction | Native tool calling in Claude Code |
| **Memory persistence** | Requires separate storage | Built-in memory store/retrieve/search |
| **Help system** | Static documentation | Progressive contextual help with `help_lookup` |
| **Authentication** | Manual API key handling | Integrated auth status and recommendations |
| **Telemetry** | Manual tracking | Automated cost tracking and performance metrics |
| **Workflow execution** | Direct function calls | MCP tool-mediated with session context |

## Performance tradeoffs

**MCP server is ~2x slower per operation** due to JSON serialization overhead, but provides significant workflow advantages:

- **Interactive sessions**: Claude Code can maintain context across multiple tool calls
- **Progressive help**: `help_lookup` escalates from concept → task → reference automatically
- **Memory coordination**: Cross-conversation pattern storage via `memory_store`
- **Cost optimization**: Built-in telemetry shows savings from cache hits and tier routing

**Direct API is faster for batch operations** but requires manual orchestration of authentication, rate limiting, and error handling.

## Use MCP server when

- You're working in Claude Code and want native tool integration
- You need session-aware workflows with context preservation
- You want progressive help that adapts based on your experience level
- You're building conversational interfaces that benefit from memory persistence
- You need built-in telemetry and cost tracking

## Use direct Python API when

- You're writing automated scripts or CI/CD pipelines
- You need access to internal classes like `RateLimiter` or `WorkflowHandlersMixin`
- Performance is critical and you can handle orchestration manually
- You're building custom integrations outside the Claude Code ecosystem
- You need functionality not exposed through the 15 MCP tools

## Recommendation

**Start with MCP server** for interactive development work. The productivity gains from integrated help, memory, and Claude Code tool calling typically outweigh the performance overhead. Switch to direct API only when you hit specific limitations or need maximum performance for batch operations.
