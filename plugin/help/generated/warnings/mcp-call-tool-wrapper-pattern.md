---
type: warning
name: mcp-call-tool-wrapper-pattern
confidence: Verified
tags: [testing, claude-code]
source: .claude/CLAUDE.md
---

# Warning: MCP `call_tool` wrapper pattern

## Condition

When adding a cross-cutting concern (like voice layer) to the MCP server, rename the original `call_tool()` to `_dispatch_tool()` and create a new `call_tool()` that wraps it

## Risk

Ignoring this guidance may cause: MCP `call_tool` wrapper pattern

## Mitigation

1. When adding a cross-cutting concern (like voice layer) to the MCP server, rename the original `call_tool()` to `_dispatch_tool()` and create a new `call_tool()` that wraps it

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: MCP `call_tool` wrapper pattern
