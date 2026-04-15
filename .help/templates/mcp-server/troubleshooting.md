---
type: troubleshooting
feature: mcp-server
depth: troubleshooting
generated_at: 2026-04-14T15:00:29.842879+00:00
source_hash: bcc1c0a657ed14e3ecc0ddf2aa190500d4decf1e455d572148863bce6b9d9c27
status: generated
---

# Troubleshoot mcp server

## Before you start

The Attune AI MCP Server provides tool handlers for memory operations, workflow execution, authentication, telemetry, and contextual help through the Model Context Protocol.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Server fails to start | Run `python -m attune.mcp.server` and check for import errors or missing dependencies |
| Tool calls return errors | Verify the tool name exists in `get_tool_list()` output and arguments match the schema |
| Rate limiting errors | Check if calls exceed 60 per minute - inspect `RateLimiter.check()` return value |
| Memory tools fail | Confirm attune-ai memory module is installed: `pip list \| grep attune-ai` |
| Prompt not found | Verify prompt name exists in the prompts dictionary returned by `get_prompt_list()` |
| Authentication issues | Check `auth_status` tool output for current configuration and subscription tier |

## Step-by-step diagnosis

1. **Test the server startup.**
   Run the MCP server directly to isolate startup issues:
   ```bash
   python -m attune.mcp.server
   ```
   If this fails, the error message will show missing dependencies or configuration problems.

2. **Verify tool availability.**
   Use `get_tool_list()` to confirm which tools are registered:
   ```python
   from attune.mcp.server import create_server
   server = create_server()
   tools = server.get_tool_list()
   print([tool['name'] for tool in tools])
   ```

3. **Test individual tool calls.**
   Call tools directly through the server to bypass MCP protocol issues:
   ```python
   result = server.call_tool("auth_status", {})
   print(result)
   ```

4. **Check rate limiting.**
   If tools intermittently fail, test the rate limiter:
   ```python
   from attune.mcp.rate_limiter import RateLimiter
   limiter = RateLimiter(max_calls=60, window_seconds=60.0)
   print(limiter.check("test_key"))  # Should return True initially
   ```

5. **Validate prompt handling.**
   Test prompt retrieval and message generation:
   ```python
   prompts = server.get_prompt_list()
   messages = server.get_prompt_messages("security-scan", {"path": "/tmp"})
   ```

## Common fixes

- **Missing memory module.** Install the memory dependency:
  ```bash
  pip install attune-ai
  ```

- **Rate limit exceeded.** The default limit is 60 calls per minute. Wait for the window to reset or increase limits if running automated tests.

- **Invalid tool arguments.** Check the tool schema in `get_utility_tools()`, `get_help_tools()`, `get_memory_tools()`, or `get_workflow_tools()` output for required parameters and types.

- **Workspace root not set.** Some tools require a workspace context. Initialize the server with a valid path:
  ```python
  server = EmpathyMCPServer(workspace_root="/path/to/project")
  ```

- **Unknown prompt error.** The prompt name must exactly match one from `get_prompt_list()`. Valid prompts are: `security-scan`, `test-gen`, and `cost-report`.

## Source files

- `src/attune/mcp/server.py` - Main EmpathyMCPServer class and entry point
- `src/attune/mcp/tool_schemas.py` - Tool definitions and schemas
- `src/attune/mcp/prompts.py` - Prompt handling functions
- `src/attune/mcp/rate_limiter.py` - Rate limiting implementation
- `src/attune/mcp/memory_handlers.py` - Memory tool handlers
- `src/attune/mcp/workflow_handlers.py` - Workflow tool handlers

**Tags:** `mcp`, `tools`, `server`
