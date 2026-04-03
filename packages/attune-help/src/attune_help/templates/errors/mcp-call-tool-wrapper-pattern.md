---
type: error
name: mcp-call-tool-wrapper-pattern
confidence: Verified
tags: [testing, claude-code]
source: .claude/CLAUDE.md
---

# Error: MCP `call_tool` wrapper pattern

## Signature

MCP `call_tool` wrapper pattern

## Root Cause

When adding a cross-cutting concern (like voice layer) to the MCP server, rename the original `call_tool()` to `_dispatch_tool()` and create a new `call_tool()` that wraps it. This preserves the public API, keeps the diff minimal, and lets the wrapper degrade gracefully with a try/except around the new layer.

## Resolution

1. When adding a cross-cutting concern (like voice layer) to the MCP server, rename the original `call_tool()` to `_dispatch_tool()` and create a new `call_tool()` that wraps it

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
