---
type: error
name: verify-mcp-tool-wiring-after-adding-new-tools
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: Verify MCP tool wiring after adding new tools

## Signature

Verify MCP tool wiring after adding new tools

## Root Cause

After adding tools to `server.py`, grep all plugin skills and commands for references. 15 tools were registered but unreachable from any skill until explicitly wired into existing skill documentation.

## Resolution

1. After adding tools to `server.py`, grep all plugin skills and commands for references

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
