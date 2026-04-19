---
type: error
feature: mcp-server
depth: error
generated_at: 2026-04-19T18:48:36.190262+00:00
source_hash: 4d53983ae8928abce86e5e58e1d186acd20ca65e85b505d31acc051216daed33
status: generated
---

# MCP server errors

Failures in the Attune AI Model Context Protocol server implementation, including prompt handling, tool execution, and rate limiting.

## Common error signatures

- `ValueError: Unknown prompt: {prompt_name}` — from `get_prompt_messages()` when requesting a prompt that doesn't exist
- `ImportError` with message `attune-ai memory module not installed` — when memory tools are called but the memory module is missing
- Rate limiting errors from `RateLimiter.check()` — when tool calls exceed the sliding window limit (default: 60 calls per 60 seconds)
- JSON schema validation errors — when tool arguments don't match the expected schema format
- Authentication errors — when `auth_status` or `auth_recommend` tools can't access authentication configuration

## Where errors originate

MCP server errors typically emerge from these components:

**Prompt handling**
- `get_prompt_messages()` validates prompt names and raises `ValueError` for unknown prompts
- Prompt argument validation fails when required arguments are missing

**Tool execution**
- `call_tool()` validates tool names and arguments before dispatching to handler methods
- Rate limiting in `RateLimiter.check()` when key-based call counts exceed thresholds
- Memory tools fail with import errors when the memory module is unavailable

**Server initialization**
- `create_server()` and `EmpathyMCPServer.__init__()` fail when workspace or user configuration is invalid
- Tool schema registration errors when schema definitions are malformed

## How to diagnose

1. **Check the prompt name exactly.** For `ValueError: Unknown prompt` errors, verify the prompt name matches entries in the prompts dictionary. Available prompts include `security-scan`, `test-gen`, and `cost-report`.

2. **Verify memory module installation.** If you see memory-related import errors, install the memory module with `pip install attune-ai` or disable memory tools if not needed.

3. **Monitor rate limiting.** If tools fail intermittently, check if you're exceeding the rate limit (60 calls per 60 seconds by default). The `RateLimiter` tracks calls per key in a sliding window.

4. **Validate tool arguments.** Tool execution failures often stem from missing required arguments or incorrect types. Check the tool schema definitions in `get_utility_tools()`, `get_help_tools()`, and `get_memory_tools()` for the expected format.

5. **Test server creation in isolation.** If the MCP server fails to start, create an `EmpathyMCPServer` instance directly to isolate initialization problems from runtime tool execution issues.

## Source files

- `src/attune/mcp/server.py` — Main server class and entry point
- `src/attune/mcp/prompts.py` — Prompt list and message handling
- `src/attune/mcp/tool_schemas.py` — Tool definitions and schemas
- `src/attune/mcp/rate_limiter.py` — Request rate limiting
- `src/attune/mcp/memory_handlers.py` — Memory tool implementations
- `src/attune/mcp/workflow_handlers.py` — Workflow tool implementations

**Tags:** `mcp`, `tools`, `server`
