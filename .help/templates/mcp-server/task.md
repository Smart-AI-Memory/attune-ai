---
type: task
feature: mcp-server
depth: task
generated_at: 2026-04-19T18:47:50.987019+00:00
source_hash: 4d53983ae8928abce86e5e58e1d186acd20ca65e85b505d31acc051216daed33
status: generated
---

# Work with mcp server

Use the MCP server when you need to integrate Attune AI workflows with Model Context Protocol clients or add new tool capabilities.

## Prerequisites

- Access to the project source code
- Familiarity with the files under `src/attune/mcp/**`
- Understanding of Model Context Protocol (MCP) specification

## Examine the server structure

1. Review the `EmpathyMCPServer` class in `src/attune/mcp/server.py` to understand the core server implementation
2. Check the tool definitions in `src/attune/mcp/tool_schemas.py`:
   - Workflow tools for task execution
   - Utility tools for auth, telemetry, and session management
   - Help tools for contextual documentation
   - Memory tools for data storage and retrieval
3. Examine the prompt definitions in `src/attune/mcp/prompts.py` for available templates

## Add new tool functionality

1. Define your tool schema in the appropriate function in `src/attune/mcp/tool_schemas.py`:
   - Add to `get_workflow_tools()` for task execution tools
   - Add to `get_utility_tools()` for system management tools
   - Add to `get_help_tools()` for documentation tools
   - Add to `get_memory_tools()` for data persistence tools

2. Implement the tool handler in the relevant mixin class:
   - Use `WorkflowHandlersMixin` for workflow execution
   - Use `MemoryHandlersMixin` for memory operations
   - Create a new mixin for other tool categories

3. Register the tool handler in `EmpathyMCPServer.call_tool()` method

## Test your changes

1. Start the MCP server with `python -m attune.mcp.server`
2. Connect a compatible MCP client to test your new functionality
3. Verify tool definitions appear in the tool list
4. Run specific tool calls to confirm proper execution
5. Execute `pytest -k "mcp"` to run automated tests

## Verification

Your MCP server changes work correctly when:
- New tools appear in the client's tool list
- Tool calls execute without errors and return expected responses
- The server maintains rate limiting (60 calls per 60 seconds by default)
- All existing functionality continues to work
