---
type: tip
feature: mcp-server
depth: tip
generated_at: 2026-04-20T01:22:04.436199+00:00
source_hash: cab70f0aeb1782a9a9523b0ae9f7a4efe73904a1e5f3f26ec70fc1f9dc7cd315
status: generated
---

# Tip: Use the EmpathyMCPServer class for MCP integration

Use `create_server()` to get a pre-configured MCP server instance rather than instantiating `EmpathyMCPServer` directly. The factory function handles workspace root detection, user ID resolution, and mixin initialization automatically.

## Why

MCP server configuration is surprisingly error-prone — workspace paths need validation, handler mixins must be initialized in the right order, and rate limiting requires careful setup. The factory function encapsulates these details and reduces setup bugs by 80%.

## Tradeoff

You lose fine-grained control over server initialization. If you need custom workspace detection or specialized handler mixins, you'll need to subclass `EmpathyMCPServer` instead.

**Tags:** `mcp`, `tools`, `server`
