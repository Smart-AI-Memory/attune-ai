---
type: warning
feature: mcp-server
depth: warning
generated_at: 2026-04-14T15:00:11.649517+00:00
source_hash: bcc1c0a657ed14e3ecc0ddf2aa190500d4decf1e455d572148863bce6b9d9c27
status: generated
---

# MCP Server cautions

## What to watch for

The Attune AI MCP server coordinates multiple tool handlers and maintains session state that can lead to unexpected behavior.

## Risk areas

### Rate limiting bypasses in concurrent tool calls

The `RateLimiter` uses a sliding window with key-based tracking, but concurrent calls with the same key can race through the `check()` method before the window updates. This allows burst calls to exceed the 60-call limit.

### Memory tool authentication failures

Memory operations (`memory_store`, `memory_retrieve`, `memory_search`, `memory_forget`) fail silently when the attune-ai memory module isn't installed, returning the constant `_MEMORY_NOT_INSTALLED` instead of raising an exception. Your code may continue executing with incomplete data.

### Prompt argument validation gaps

`get_prompt_messages()` raises `ValueError` for unknown prompts but doesn't validate that required arguments are provided. Missing arguments for prompts like `security-scan` (which requires a `path`) will cause downstream failures in the workflow execution.

### Tool handler state isolation

`EmpathyMCPServer` combines multiple mixins (`MemoryHandlersMixin`, `WorkflowHandlersMixin`) that each maintain internal state. Changes to one handler can affect others through shared instance variables, particularly the `user_id` and `workspace_root` initialization parameters.

### Voice tool filtering inconsistencies

The `_VOICE_SKIP_TOOLS` constant excludes specific tools from voice interfaces, but this list is maintained separately from tool registration. Adding new tools requires updating both the tool schema definitions and this exclusion list.

## How to avoid problems

1. **Test rate limiting under load.** When using `RateLimiter`, verify behavior with concurrent requests: `asyncio.gather(*[limiter.check(key) for _ in range(100)])` should respect the limits even under contention.

2. **Check memory module availability early.** Before relying on memory tools, verify installation: `pip show attune-ai` or catch the `_MEMORY_NOT_INSTALLED` response and handle gracefully.

3. **Validate prompt arguments explicitly.** When calling `get_prompt_messages()`, check that all required arguments from the prompt definition are present before passing to the function.

4. **Initialize server instances cleanly.** Pass explicit `workspace_root` and `user_id` values to `EmpathyMCPServer()` rather than relying on defaults, and avoid sharing instances across different user contexts.

5. **Audit tool visibility changes.** When adding new tools, decide whether they should be available in voice interfaces and update `_VOICE_SKIP_TOOLS` accordingly.

## Source files

- `src/attune/mcp/**`

**Tags:** `mcp`, `tools`, `server`
