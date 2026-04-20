---
type: troubleshooting
feature: mcp-server
depth: troubleshooting
generated_at: 2026-04-20T01:21:26.911338+00:00
source_hash: cab70f0aeb1782a9a9523b0ae9f7a4efe73904a1e5f3f26ec70fc1f9dc7cd315
status: generated
---

# Troubleshoot MCP server

## Before you start

The Attune AI MCP server provides tool handlers, prompts, and resources for Model Context Protocol clients like Claude Code. Common issues include server startup failures, tool call timeouts, and authentication problems.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Server won't start or exits immediately | Process logs and `.mcp.json` configuration |
| Tool calls timeout or hang | Rate limiter state and tool handler exceptions |
| Authentication errors | User ID setup and workspace root permissions |
| Missing tools in client | Tool schema registration and server handshake |
| Memory operations fail | Memory module installation and database access |

## Step-by-step diagnosis

1. **Verify server startup**
   Test the server directly: `uv run python -m attune.mcp.server`
   Check for import errors, missing dependencies, or configuration issues.

2. **Check MCP configuration**
   Ensure `.mcp.json` exists in your project root with correct command syntax:
   ```json
   {
     "mcpServers": {
       "attune": {
         "command": "uv",
         "args": ["run", "--from", "attune-ai", "python", "-m", "attune.mcp.server"]
       }
     }
   }
   ```

3. **Test tool registration**
   Call `EmpathyMCPServer().get_tool_list()` to verify tools are properly registered.
   Missing tools indicate schema loading failures or import problems.

4. **Examine rate limiting**
   The `RateLimiter` (60 calls per 60 seconds) may be blocking requests.
   Check recent call patterns and consider if you've exceeded limits.

5. **Validate workspace setup**
   Confirm the server can access your workspace root and has proper file permissions.
   Memory tools require write access to store session data.

## Common fixes

- **Missing dependencies:** Install the memory module with `pip install attune-ai[memory]` if memory tools fail
- **Permission errors:** Ensure the server process can read/write in the workspace directory
- **Rate limit exceeded:** Wait for the sliding window to reset or restart the server to clear limits
- **Stale processes:** Kill existing MCP server processes with `pkill -f "attune.mcp.server"` before restarting
- **Configuration mismatch:** Use `uv run --from attune-ai` in `.mcp.json` to ensure correct package resolution

## Source files

- `src/attune/mcp/server.py` — Main server implementation and entry point
- `src/attune/mcp/tool_schemas.py` — Tool definitions and handlers
- `src/attune/mcp/prompts.py` — Prompt handling and message generation
- `src/attune/mcp/rate_limiter.py` — Request rate limiting
- `src/attune/mcp/memory_handlers.py` — Memory tool implementations

**Tags:** `mcp`, `tools`, `server`
