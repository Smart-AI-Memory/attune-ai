---
feature: mcp-server
depth: reference
generated_at: 2026-04-13T18:07:44.226844+00:00
source_hash: 573bf0d5245dd536c1752066c5919eba5993fb627889d8b4e69163436a9206ef
status: generated
---

# Mcp Server reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `MemoryHandlersMixin` | Mixin providing memory tool handlers for EmpathyMCPServer. | `src/attune/mcp/memory_handlers.py` |
| `RateLimiter` | Simple sliding-window rate limiter. | `src/attune/mcp/rate_limiter.py` |
| `EmpathyMCPServer` | MCP server for Attune AI workflows. | `src/attune/mcp/server.py` |
| `WorkflowHandlersMixin` | Mixin providing workflow tool handlers for EmpathyMCPServer. | `src/attune/mcp/workflow_handlers.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `get_prompt_list()` | Get list of available prompts. | `src/attune/mcp/prompts.py` |
| `get_prompt_messages()` | Get messages for a specific prompt. | `src/attune/mcp/prompts.py` |
| `create_server()` | Create and return an Empathy MCP server instance. | `src/attune/mcp/server.py` |
| `main()` | Entry point for MCP server. | `src/attune/mcp/server.py` |
| `get_workflow_tools()` | Tool definitions for workflow execution tools. | `src/attune/mcp/tool_schemas.py` |
| `get_utility_tools()` | Tool definitions for auth, telemetry, and session management. | `src/attune/mcp/tool_schemas.py` |
| `get_help_tools()` | Tool definitions for contextual help and progressive documentation. | `src/attune/mcp/tool_schemas.py` |
| `get_memory_tools()` | Tool definitions for memory store/retrieve/search/forget. | `src/attune/mcp/tool_schemas.py` |
| `get_resources()` | MCP resource definitions. | `src/attune/mcp/tool_schemas.py` |
| `get_prompts()` | MCP prompt definitions. | `src/attune/mcp/tool_schemas.py` |
| `check_for_updates()` | Check PyPI for a newer version of attune-ai. | `src/attune/mcp/version_check.py` |
| `get_update_status()` | Get cached update status. | `src/attune/mcp/version_check.py` |


## Source files

- `src/attune/mcp/**`

## Tags

`mcp`, `tools`, `server`
