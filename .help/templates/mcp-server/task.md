---
feature: mcp-server
depth: task
generated_at: 2026-04-04T02:25:50.285850+00:00
source_hash: 348722576514772ba6d54fddad36123bea1b0db23f2bf280ad6f23a2b54e679b
status: generated
---

# Working with Mcp Server

## Overview

Common tasks for modifying or extending mcp server.

## Key Files

- `src/attune/mcp/**`


## Common Modifications

Functions you may need to modify:

- `get_prompt_list()` in `src/attune/mcp/prompts.py`

- `get_prompt_messages()` in `src/attune/mcp/prompts.py`

- `create_server()` in `src/attune/mcp/server.py`

- `main()` in `src/attune/mcp/server.py`

- `get_workflow_tools()` in `src/attune/mcp/tool_schemas.py`

- `get_utility_tools()` in `src/attune/mcp/tool_schemas.py`

- `get_help_tools()` in `src/attune/mcp/tool_schemas.py`

- `get_memory_tools()` in `src/attune/mcp/tool_schemas.py`
