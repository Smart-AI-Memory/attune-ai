---
type: troubleshooting
feature: mcp-server
depth: troubleshooting
generated_at: 2026-04-19T18:49:08.551770+00:00
source_hash: 4d53983ae8928abce86e5e58e1d186acd20ca65e85b505d31acc051216daed33
status: generated
---

# Troubleshoot MCP server

## Before you start

The Attune AI MCP (Model Context Protocol) server provides tools, prompts, and resources for AI workflows. When it fails, check connection, configuration, and tool registration first.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Server fails to start | `.mcp.json` configuration and Python environment path |
| Tools not available in client | `get_tool_list()` output and rate limiter status |
| Prompts missing or malformed | Prompt definitions in `get_prompts()` |
| Memory tools fail | `attune-ai` package installation and user permissions |
| Rate limit errors | `RateLimiter` window settings (default: 60 calls/60 seconds) |
| Authentication failures | Workspace root permissions and user ID configuration |

## Step-by-step diagnosis

1. **Test server startup manually.**
   Run `python -m attune.mcp.server` to check if the server starts without client interaction. Look for import errors, missing dependencies, or configuration issues.

2. **Verify MCP client configuration.**
   Check that `.mcp.json` points to the correct Python executable. Use `uv run python -m attune.mcp.server` rather than bare `python` to ensure proper environment resolution.

3. **Check tool registration.**
   Call `EmpathyMCPServer.get_tool_list()` directly to verify tools are properly registered. Missing tools indicate initialization problems in the handler mixins.

4. **Test rate limiting.**
   If tools intermittently fail, check the `RateLimiter` with `check("test_key")` calls. The default allows 60 calls per 60-second window.

5. **Examine memory tool dependencies.**
   Memory tools require the `attune-ai` package. If you see "memory module not installed" errors, run `pip install attune-ai`.

## Common fixes

- **Fix environment resolution:** Update `.mcp.json` to use `uv run --from attune-ai python -m attune.mcp.server` for guaranteed package resolution.
- **Reset rate limiter:** Restart the server to clear rate limiting state, or adjust limits in `RateLimiter.__init__()`.
- **Install missing dependencies:** Run `pip install attune-ai` if memory tools fail with import errors.
- **Set workspace permissions:** Ensure the user running the server has read/write access to the workspace root directory.
- **Restart MCP client:** After fixing server configuration, restart your MCP client (like Claude Code) to re-establish the connection.

## Source files

- `src/attune/mcp/server.py` - Main server implementation and entry point
- `src/attune/mcp/tool_schemas.py` - Tool definitions and schemas
- `src/attune/mcp/prompts.py` - Prompt handling
- `src/attune/mcp/handlers/` - Tool handler mixins

**Tags:** `mcp`, `tools`, `server`
