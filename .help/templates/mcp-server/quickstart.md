---
type: quickstart
feature: mcp-server
depth: quickstart
generated_at: 2026-04-20T01:21:55.177295+00:00
source_hash: cab70f0aeb1782a9a9523b0ae9f7a4efe73904a1e5f3f26ec70fc1f9dc7cd315
status: generated
---

# Quickstart: Run the MCP Server

Start Attune's Model Context Protocol server and make your first tool call.

```python
from attune.mcp.server import create_server

# Create and start the MCP server
server = create_server()

# Get available tools
tools = server.get_tool_list()
print(f"Available tools: {[tool['name'] for tool in tools]}")

# Make your first tool call
result = server.call_tool('auth_status', {})
print(f"Auth status: {result}")
```

Expected output:
```
Available tools: ['auth_status', 'help_lookup', 'memory_store', ...]
Auth status: {'status': 'configured', 'tier': 'free', 'mode': 'hybrid'}
```

## Next steps

1. **Try a help lookup**
   ```python
   help_result = server.call_tool('help_lookup', {'topic': 'security-audit'})
   print(help_result)
   ```

2. **Run a prompt**
   ```python
   prompts = server.get_prompt_list()
   messages = server.get_prompt_messages('security-scan', {'path': '.'})
   ```

3. **Check available resources**
   ```python
   resources = server.get_resource_list()
   for resource in resources:
       print(f"{resource['name']}: {resource['description']}")
   ```

## What you just did

You created an MCP server instance that provides 20+ tools for workflow execution, help lookup, memory management, and authentication. The server handles rate limiting, user context, and progressive help automatically.

## Next

Say **"show me MCP server tools"** to see the complete tool reference with all parameters and return types.
