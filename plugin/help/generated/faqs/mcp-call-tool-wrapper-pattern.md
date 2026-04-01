---
type: faq
name: mcp-call-tool-wrapper-pattern
tags: [testing, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about MCP call_tool wrapper pattern?

## Answer

When adding a cross-cutting concern (like voice layer) to the MCP server, rename the original `call_tool()` to `_dispatch_tool()` and create a new `call_tool()` that wraps it. This preserves the public API, keeps the diff minimal, and lets the wrapper degrade gracefully with a try/except around the new layer.

```
call_tool()
```

## Related Topics
- **Error**: Detailed error: MCP `call_tool` wrapper pattern
