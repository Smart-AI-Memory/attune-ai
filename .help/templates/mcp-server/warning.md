---
type: warning
feature: mcp-server
depth: warning
generated_at: 2026-04-19T18:48:54.500398+00:00
source_hash: 4d53983ae8928abce86e5e58e1d186acd20ca65e85b505d31acc051216daed33
status: generated
---

# MCP Server cautions

## Rate limiting can silently drop tool calls

The `RateLimiter` class enforces a 60-call/60-second window by default. When the limit is exceeded, `check()` returns `False` but doesn't raise an exception. This means your tool calls will appear to succeed but produce no output.

**Mitigation:** Monitor the return value of `RateLimiter.check()` and handle rate limit failures explicitly. Consider adjusting the limits based on your actual usage patterns.

## Tool registration happens at server creation time

The `EmpathyMCPServer` builds its tool registry in `__init__()` by calling `get_workflow_tools()`, `get_utility_tools()`, `get_help_tools()`, and `get_memory_tools()`. Tools added after server creation won't be available to clients.

**Mitigation:** Register all tools before calling `create_server()`. If you need dynamic tool registration, restart the server instance rather than trying to modify the existing registry.

## Prompt arguments are not validated until execution

`get_prompt_messages()` accepts any `arguments` dictionary but only validates required parameters when the prompt is actually retrieved. This means invalid arguments will cause runtime failures during tool execution rather than at setup time.

**Mitigation:** Test prompt execution with representative arguments during development. The error message will tell you exactly which required argument is missing.

## Memory tools fail silently when not installed

If the `attune-ai` package isn't installed, memory tools (`memory_store`, `memory_retrieve`, etc.) return an error message instead of raising an exception. This can mask dependency issues in production.

**Mitigation:** Check the return value of memory operations for the string "attune-ai memory module not installed" and handle it as a configuration error.

## Session context persists across tool calls

The `context_get` and `context_set` utilities maintain state in the server instance. Context set in one tool call remains available to subsequent calls, which can create unexpected dependencies between operations.

**Mitigation:** Treat session context as shared state. Clear context explicitly when starting new workflows, and avoid using context keys that might conflict across different operations.

## Source files

- `src/attune/mcp/**`

**Tags:** `mcp`, `tools`, `server`
