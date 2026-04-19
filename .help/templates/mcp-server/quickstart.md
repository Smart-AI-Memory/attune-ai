---
type: quickstart
feature: mcp-server
depth: quickstart
generated_at: 2026-04-19T18:49:35.787752+00:00
source_hash: 4d53983ae8928abce86e5e58e1d186acd20ca65e85b505d31acc051216daed33
status: generated
---

# Quickstart: MCP Server

Start an Attune MCP server that provides AI workflows, memory management, and contextual help through the Model Context Protocol.

```python
from attune.mcp import create_server

# Create and start the server
server = create_server()
print("MCP server ready with tools:", len(server.get_tool_list()))
```

Expected output:
```
MCP server ready with tools: 15
```

## Step 1: Create the server instance

The `create_server()` function returns a configured `EmpathyMCPServer` with all tool handlers loaded:

```python
from attune.mcp import create_server

server = create_server()
```

## Step 2: Verify available capabilities

Check what the server provides:

```python
# List all available tools
tools = server.get_tool_list()
print(f"Available tools: {len(tools)}")

# List available prompts
prompts = server.get_prompt_list()
print(f"Available prompts: {len(prompts)}")
```

You should see 15+ tools including `help_lookup`, `memory_store`, `workflow_run`, and authentication utilities.

## Step 3: Test a basic tool call

Try the help lookup tool to verify everything works:

```python
result = server.call_tool("help_lookup", {"topic": "security"})
print(result["content"])
```

This returns contextual help about security workflows and patterns.

## What you just did

- Created an MCP server instance with all Attune capabilities
- Verified the server loaded workflow, memory, and help tools
- Tested basic functionality with a tool call

## Next

Run the server as a standalone process with `python -m attune.mcp.server` to connect it to MCP-compatible clients like Claude Desktop.
