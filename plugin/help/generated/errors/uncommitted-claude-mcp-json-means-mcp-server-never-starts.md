---
type: error
name: uncommitted-claude-mcp-json-means-mcp-server-never-starts
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Error: Uncommitted `.claude/mcp.json` means MCP server never
  starts

## Signature

Uncommitted `.claude/mcp.json` means MCP server never
  starts

## Root Cause

Claude Code reads the *committed* version of `.claude/mcp.json` at session start. If the working copy has fixes (like removing `"disabled": true` or changing `"command": "python"` to `"command": "uv"`) but they're not committed, the MCP server won't connect. Always commit MCP config changes immediately — an uncommitted fix is invisible to new sessions.

## Resolution

1. Always commit MCP config changes immediately — an uncommitted fix is invisible to new sessions

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Uncommitted `.claude/mcp.json` means MCP server never
  starts
