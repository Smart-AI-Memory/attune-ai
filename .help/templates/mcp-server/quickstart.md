---
type: quickstart
feature: mcp-server
depth: quickstart
generated_at: 2026-04-14T15:01:01.144977+00:00
source_hash: bcc1c0a657ed14e3ecc0ddf2aa190500d4decf1e455d572148863bce6b9d9c27
status: generated
---

# Quickstart: MCP Server

Run the Attune AI Model Context Protocol server to expose workflows, memory, and help tools to MCP-compatible clients.

```python
from attune.mcp.server import create_server

server = create_server()
print(f"Server created with {len(server.get_tool_list())} tools")
```

**Expected output:**
```
Server created with 15 tools
```

## Start the server

1. **Create the server instance** using `create_server()` which configures the workspace root and user context automatically.

2. **Launch the MCP server** by running the main entry point:
   ```bash
   python -m attune.mcp.server
   ```

3. **Verify available tools** by checking the tool list includes workflow execution, memory operations, authentication status, and contextual help tools.

## Test tool access

Call a tool through the server to confirm it's working:

```python
# Check authentication status
result = server.call_tool("auth_status", {})
print(result["status"])  # Shows current auth configuration

# Get available workflows
workflows = server.call_tool("help_lookup", {"topic": "workflows"})
print(f"Found {len(workflows)} workflow descriptions")
```

**Expected output:**
```
authenticated
Found 12 workflow descriptions
```

**Next:** Connect your MCP client (like Claude Desktop) to the running server to access Attune AI tools directly from your AI assistant.
