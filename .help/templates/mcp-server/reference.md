---
feature: mcp-server
depth: reference
generated_at: 2026-04-06T04:30:08.860149+00:00
source_hash: 64f150abed667e764233b86a01bfe7000bb8f4d6507efcca218ef09579d9f90e
status: generated
---

# MCP server reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `MemoryHandlersMixin` | Provides memory tool handlers for storing, retrieving, searching, and forgetting data. | `src/attune/mcp/memory_handlers.py` |
| `RateLimiter` | Controls request frequency using a sliding-window algorithm to prevent MCP tool call abuse. | `src/attune/mcp/rate_limiter.py` |
| `EmpathyMCPServer` | Serves Attune AI workflow capabilities through the Model Context Protocol interface. | `src/attune/mcp/server.py` |
| `WorkflowHandlersMixin` | Provides workflow execution tool handlers for the MCP server. | `src/attune/mcp/workflow_handlers.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `get_prompt_list()` | Returns available prompt templates for the MCP server. | `src/attune/mcp/prompts.py` |
| `get_prompt_messages()` | Returns formatted messages for a specific prompt template. | `src/attune/mcp/prompts.py` |
| `create_server()` | Creates a configured Empathy MCP server instance with all handlers enabled. | `src/attune/mcp/server.py` |
| `main()` | Starts the MCP server and handles client connections. | `src/attune/mcp/server.py` |
| `get_workflow_tools()` | Defines MCP tools for executing Attune AI workflows. | `src/attune/mcp/tool_schemas.py` |
| `get_utility_tools()` | Defines MCP tools for authentication, telemetry, and session management. | `src/attune/mcp/tool_schemas.py` |
| `get_help_tools()` | Defines MCP tools for contextual help and progressive documentation. | `src/attune/mcp/tool_schemas.py` |
| `get_memory_tools()` | Defines MCP tools for memory operations including store, retrieve, search, and forget. | `src/attune/mcp/tool_schemas.py` |
| `get_resources()` | Defines available MCP resources that clients can access. | `src/attune/mcp/tool_schemas.py` |
| `get_prompts()` | Defines prompt templates available through the MCP protocol. | `src/attune/mcp/tool_schemas.py` |
| `check_for_updates()` | Queries PyPI to determine if a newer version of attune-ai is available. | `src/attune/mcp/version_check.py` |
| `get_update_status()` | Returns cached version comparison results from the last update check. | `src/attune/mcp/version_check.py` |

## Source files

- `src/attune/mcp/**`

## Tags

`mcp`, `tools`, `server`
