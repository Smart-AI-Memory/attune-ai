---
name: mcp-call-tool-wrapper-pattern
source: .claude/CLAUDE.md
summary: This template explains how to use the wrapper pattern in MCP servers to add
  cross-cutting concerns like a voice layer by renaming the original `call_tool()`
  to `_dispatch_tool()` and creating a new `call_tool()` wrapper that preserves the
  API, minimizes code changes, and enables graceful error handling.
tags:
- testing
- claude-code
type: faq
---

# FAQ: What should I know about the MCP `call_tool` wrapper pattern?

## Answer

When adding a cross-cutting concern (such as a voice layer) to an MCP server, use the wrapper pattern:

1. Rename the original `call_tool()` to `_dispatch_tool()`.
2. Create a new `call_tool()` that calls `_dispatch_tool()` internally.

This approach offers several benefits:

- **Preserves the public API** — callers are unaffected by the change.
- **Minimizes the diff** — only the new wrapper and the rename are introduced.
- **Enables graceful degradation** — wrap the new layer in a `try/except` block so that failures in the cross-cutting concern (e.g., a voice synthesis error) do not break core tool dispatch.

**Example structure:**

```python
async def _dispatch_tool(self, name: str, arguments: dict):
    # Original tool dispatch logic
    ...

async def call_tool(self, name: str, arguments: dict):
    try:
        await self._add_voice_layer(name, arguments)  # cross-cutting concern
    except Exception:
        pass  # degrade gracefully if the new layer fails
    return await self._dispatch_tool(name, arguments)
```

## Related Topics

- [Error Reference: MCP `call_tool` wrapper pattern](./mcp-call-tool-error-reference.md)
