---
type: error
feature: mcp-server
depth: error
generated_at: 2026-04-20T01:20:52.310827+00:00
source_hash: cab70f0aeb1782a9a9523b0ae9f7a4efe73904a1e5f3f26ec70fc1f9dc7cd315
status: generated
---

# MCP server errors

This page covers failures in the Attune AI Model Context Protocol server, including tool invocation errors, prompt loading failures, and rate limiting issues.

## Common error signatures

**Prompt-related errors:**
- `ValueError: Unknown prompt: {prompt_name}` — from `get_prompt_messages()` when requesting a non-existent prompt
- `KeyError` — when prompt template references missing arguments

**Rate limiting errors:**
- Tool calls that silently fail or get delayed when exceeding 60 calls per minute
- Inconsistent response times during burst usage

**Memory tool errors:**
- `RuntimeError: attune-ai memory module not installed. Run: pip install attune-ai` — when memory tools are called without the optional dependency
- Authentication errors when memory classification levels don't match user permissions

**Server initialization errors:**
- `FileNotFoundError` — when workspace_root points to a non-existent directory
- Import errors if MCP dependencies are missing

## Where errors originate

**Prompt system:**
- `get_prompt_messages()` raises `ValueError` for unknown prompt names
- Template rendering fails when required arguments are missing from the request

**Tool handlers:**
- `EmpathyMCPServer.call_tool()` validates tool names and delegates to specific handlers
- Memory tools fail fast with installation check before attempting operations
- Help tools can fail during template generation or file system access

**Rate limiter:**
- `RateLimiter.check()` tracks call windows but doesn't raise exceptions — instead returns `False` for rate-limited requests
- Rate limit state is per-key, so different tools can have independent limits

**Server lifecycle:**
- `create_server()` initializes with workspace validation
- `main()` handles MCP protocol setup and can fail during transport initialization

## How to diagnose

1. **Check the tool name first.** If you're getting errors during tool calls, verify the tool name exists in the output of `get_tool_list()`. The MCP server has specific tools for workflows, utilities, help, and memory.

2. **Verify prompt arguments.** For prompt-related `ValueError` exceptions, compare your prompt name against the list from `get_prompt_list()`. For template errors, ensure all required arguments are provided in your request.

3. **Check memory module installation.** If memory tools fail with "module not installed", run `pip install attune-ai` to add the optional memory dependency.

4. **Monitor rate limiting.** If tools seem unresponsive or slow, you may be hitting the 60-calls-per-minute limit. The rate limiter uses a sliding window, so wait a minute and retry.

5. **Inspect workspace configuration.** Server initialization errors often trace to invalid workspace_root paths. Verify the directory exists and is accessible.

## Source files

- `src/attune/mcp/server.py` — Main server class and entry point
- `src/attune/mcp/prompts.py` — Prompt loading and template rendering
- `src/attune/mcp/tool_schemas.py` — Tool definitions and schemas
- `src/attune/mcp/memory_handlers.py` — Memory tool implementations
- `src/attune/mcp/workflow_handlers.py` — Workflow tool handlers
- `src/attune/mcp/rate_limiter.py` — Request rate limiting

**Tags:** `mcp`, `tools`, `server`
