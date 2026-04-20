---
type: warning
feature: mcp-server
depth: warning
generated_at: 2026-04-20T01:21:12.205897+00:00
source_hash: cab70f0aeb1782a9a9523b0ae9f7a4efe73904a1e5f3f26ec70fc1f9dc7cd315
status: generated
---

# MCP Server cautions

## Rate limiting can silently drop calls

The `RateLimiter` class uses a sliding window with a 60-call default limit. When you exceed this limit, `check()` returns `False` but doesn't raise an exception. Tool calls fail silently, which can make debugging difficult.

**Avoid this:** Check the rate limiter's return value before making tool calls, especially in loops or batch operations. Consider increasing the limit for heavy workflows using `RateLimiter(max_calls=200)`.

## Missing prompts cause runtime failures

The `get_prompt_messages()` function raises `ValueError` for unknown prompt names, but only at runtime. If you reference a prompt that doesn't exist in the prompt registry, you won't discover the problem until the tool is called.

**Avoid this:** Validate prompt names against `get_prompt_list()` during initialization. Test all prompt references in your integration tests.

## Tool schema validation is deferred

The MCP server defines tool schemas but doesn't validate arguments until `call_tool()` executes. Invalid arguments reach your tool handlers, where they may cause unexpected behavior or crashes.

**Avoid this:** Add explicit validation at the start of your tool handlers. Use the input schema patterns from `get_utility_tools()` and `get_help_tools()` as templates for required field checking.

## Memory tools fail without attune-ai package

Memory-related tools (`memory_store`, `memory_retrieve`, etc.) import the `attune-ai` package dynamically. If the package isn't installed, these tools fail at runtime with an import error rather than being disabled gracefully.

**Avoid this:** Check for the attune-ai dependency during server initialization. Consider making memory tools optional in your MCP client configuration.

## Workspace isolation can break file operations

The `EmpathyMCPServer` accepts a `workspace_root` parameter that scopes file operations. If you pass relative paths to tools that expect absolute paths, operations may target the wrong files or fail silently.

**Avoid this:** Always resolve relative paths against the workspace root before passing them to file-based tools. Use `os.path.abspath()` to convert relative paths in tool arguments.
