---
feature: mcp-server
depth: task
generated_at: 2026-04-13T16:56:48.682204+00:00
source_hash: cd9113c895b6740f8b406b613bcb2f3d3ed3fac586882f2d8ebc96e6107c1f5f
status: generated
---

# Work with mcp server

Use mcp server when you need to integrate Attune AI's MCP (Model Context Protocol) server with client applications or modify its memory, workflow, and prompt handling capabilities.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/mcp/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what mcp server
   does today before making changes.
   The primary functions are:
   - `get_prompt_list()` in `src/attune/mcp/prompts.py` — Get list of available prompts.
   - `get_prompt_messages()` in `src/attune/mcp/prompts.py` — Get messages for a specific prompt.
   - `create_server()` in `src/attune/mcp/server.py` — Create and return an Empathy MCP server instance.
   - `main()` in `src/attune/mcp/server.py` — Entry point for MCP server.
   - `get_workflow_tools()` in `src/attune/mcp/tool_schemas.py` — Tool definitions for workflow execution tools.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "mcp-server"`.

## Key files

- `src/attune/mcp/**`

## Common modifications

Functions you are most likely to modify:

- `get_prompt_list()` in `src/attune/mcp/prompts.py`
- `get_prompt_messages()` in `src/attune/mcp/prompts.py`
- `create_server()` in `src/attune/mcp/server.py`
- `main()` in `src/attune/mcp/server.py`
- `get_workflow_tools()` in `src/attune/mcp/tool_schemas.py`
- `get_utility_tools()` in `src/attune/mcp/tool_schemas.py`
- `get_help_tools()` in `src/attune/mcp/tool_schemas.py`
- `get_memory_tools()` in `src/attune/mcp/tool_schemas.py`
