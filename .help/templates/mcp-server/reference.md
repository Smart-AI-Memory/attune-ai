---
feature: mcp-server
depth: reference
generated_at: 2026-04-13T16:56:57.131135+00:00
source_hash: cd9113c895b6740f8b406b613bcb2f3d3ed3fac586882f2d8ebc96e6107c1f5f
status: generated
---

# MCP server reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `MemoryHandlersMixin` | Mixin that provides memory tool handlers for EmpathyMCPServer. | `src/attune/mcp/memory_handlers.py` |
| `RateLimiter` | Sliding-window rate limiter for MCP tool calls. | `src/attune/mcp/rate_limiter.py` |
| `EmpathyMCPServer` | MCP server implementation for Attune AI workflows. | `src/attune/mcp/server.py` |
| `WorkflowHandlersMixin` | Mixin that provides workflow tool handlers for EmpathyMCPServer. | `src/attune/mcp/workflow_handlers.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `get_prompt_list()` | Returns list of available prompts. | `src/attune/mcp/prompts.py` |
| `get_prompt_messages()` | Returns messages for a specific prompt. | `src/attune/mcp/prompts.py` |
| `create_server()` | Creates and returns an Empathy MCP server instance. | `src/attune/mcp/server.py` |
| `main()` | Entry point for MCP server. | `src/attune/mcp/server.py` |
| `get_workflow_tools()` | Returns tool definitions for workflow execution tools. | `src/attune/mcp/tool_schemas.py` |
| `get_utility_tools()` | Returns tool definitions for auth, telemetry, and session management. | `src/attune/mcp/tool_schemas.py` |
| `get_help_tools()` | Returns tool definitions for contextual help and progressive documentation. | `src/attune/mcp/tool_schemas.py` |
| `get_memory_tools()` | Returns tool definitions for memory store, retrieve, search, and forget operations. | `src/attune/mcp/tool_schemas.py` |
| `get_resources()` | Returns MCP resource definitions. | `src/attune/mcp/tool_schemas.py` |
| `get_prompts()` | Returns MCP prompt definitions. | `src/attune/mcp/tool_schemas.py` |
| `check_for_updates()` | Check PyPI for a newer version of attune-ai. | `src/attune/mcp/version_check.py` |
| `get_update_status()` | Get cached update status. | `src/attune/mcp/version_check.py` |


## Source files

- `src/attune/mcp/**`

## Tags

`mcp`, `tools`, `server`
