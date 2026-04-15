---
type: error
feature: mcp-server
depth: error
generated_at: 2026-04-14T14:59:54.321491+00:00
source_hash: bcc1c0a657ed14e3ecc0ddf2aa190500d4decf1e455d572148863bce6b9d9c27
status: generated
---

# MCP Server errors

MCP Server failures occur during Model Context Protocol operations, prompt handling, tool execution, and server initialization.

## Common error signatures

- `ValueError: Unknown prompt: {prompt_name}` — Prompt name not found in available prompts
- `ImportError: attune-ai memory module not installed. Run: pip install attune-ai` — Memory tools accessed without required dependency
- `AttributeError` during `EmpathyMCPServer.__init__()` — Missing workspace_root or user_id configuration
- `KeyError` during tool execution — Missing required arguments in tool calls
- `RateLimitExceeded` from `RateLimiter.check()` — Too many calls within sliding window (60 calls/60 seconds default)

## Where errors originate

MCP Server errors typically originate from these key operations:

- **Prompt resolution**: `get_prompt_messages()` fails when requesting unknown prompt names
- **Server initialization**: `create_server()` and `EmpathyMCPServer.__init__()` fail on configuration issues
- **Tool execution**: `call_tool()` fails on invalid tool names, missing arguments, or rate limiting
- **Memory operations**: Memory tool handlers fail when the attune-ai memory module isn't installed
- **Rate limiting**: `RateLimiter.check()` rejects requests exceeding the configured window limits

## How to diagnose

1. **Identify the operation context**. MCP Server errors fall into distinct categories:
   - Prompt errors: Check if the prompt name exists in `get_prompt_list()` output
   - Tool errors: Verify tool name and arguments against `get_tool_list()` schemas
   - Memory errors: Confirm attune-ai memory module installation
   - Rate limit errors: Check call frequency against configured limits

2. **Check configuration state**. Server initialization failures often stem from:
   - Missing or invalid `workspace_root` path
   - Undefined `user_id` for session management
   - Missing environment variables for authentication

3. **Validate tool arguments**. Tool execution failures typically involve:
   - Missing required arguments (check tool schema in `get_utility_tools()`, `get_memory_tools()`, etc.)
   - Invalid argument types (string vs integer, missing enum values)
   - Authentication or permission issues for protected operations

4. **Monitor rate limiting**. If you see frequent failures:
   - Check `RateLimiter` window settings (default 60 calls per 60 seconds)
   - Identify which tools are being called most frequently
   - Consider adjusting call patterns or rate limits

## Source files

- `src/attune/mcp/server.py` — Main EmpathyMCPServer implementation
- `src/attune/mcp/prompts.py` — Prompt handling and resolution
- `src/attune/mcp/tool_schemas.py` — Tool definitions and schemas
- `src/attune/mcp/memory_handlers.py` — Memory operation handlers
- `src/attune/mcp/rate_limit.py` — Request rate limiting
- `src/attune/mcp/workflow_handlers.py` — Workflow execution handlers

**Tags:** `mcp`, `tools`, `server`
