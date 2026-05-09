---
type: warning
name: uncommitted-claude-mcp-json-means-mcp-server-never-starts
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Warning: Uncommitted `.claude/mcp.json` means MCP server never
  starts

## Condition

Claude Code reads the *committed* version of `.claude/mcp.json` at session start

## Risk

Ignoring this guidance may cause: Uncommitted `.claude/mcp.json` means MCP server never
  starts

## Mitigation

1. Always commit MCP config changes immediately — an uncommitted fix is invisible to new sessions

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Uncommitted `.claude/mcp.json` means MCP server never
  starts
