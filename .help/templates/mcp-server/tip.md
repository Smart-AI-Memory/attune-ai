---
type: tip
feature: mcp-server
depth: tip
generated_at: 2026-04-14T15:01:10.384688+00:00
source_hash: bcc1c0a657ed14e3ecc0ddf2aa190500d4decf1e455d572148863bce6b9d9c27
status: generated
---

# Use `EmpathyMCPServer` for tool grouping

Start with `create_server()` to get a configured server instance, then explore its tool categories through the mixins. Each mixin groups related functionality: `MemoryHandlersMixin` for memory operations, `WorkflowHandlersMixin` for workflow execution.

The server automatically rate-limits tool calls (60 per minute by default) and provides progressive help through the `help_lookup` tool. Use the `get_tool_list()` method to see all available tools at runtime rather than hardcoding tool names.

**Why:** The mixin architecture separates concerns cleanly, making it easier to understand which tools handle what domain without digging through monolithic classes.
