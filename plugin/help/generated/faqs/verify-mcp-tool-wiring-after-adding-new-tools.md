---
type: faq
name: verify-mcp-tool-wiring-after-adding-new-tools
tags: [claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about verify MCP tool wiring after adding new tools?

## Answer

After adding tools to `server.py`, grep all plugin skills and commands for references. 15 tools were registered but unreachable from any skill until explicitly wired into existing skill documentation.

## Related Topics
- **Error**: Detailed error: Verify MCP tool wiring after adding new tools
