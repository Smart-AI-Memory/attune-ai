---
type: faq
name: uncommitted-claude-mcp-json-means-mcp-server-never-starts
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about uncommitted .claude/mcp.json means MCP server never starts?

## Answer

Claude Code reads the *committed* version of `.claude/mcp.json` at session start. If the working copy has fixes (like removing `"disabled": true` or changing `"command": "python"` to `"command": "uv"`) but they're not committed, the MCP server won't connect.

**How to fix:**
- Always commit MCP config changes immediately — an uncommitted fix is invisible to new sessions

```
.claude/mcp.json
```

## Related Topics
- **Error**: Detailed error: Uncommitted `.claude/mcp.json` means MCP server never
  starts
