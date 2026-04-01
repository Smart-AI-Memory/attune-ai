---
type: faq
name: mcp-tool-renames-propagate-to-skill-docs
tags: [claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about MCP tool renames propagate to skill docs?

## Answer

The empathy tools were renamed from `empathy_get_level`/`empathy_set_level` to `attune_get_level`/`attune_set_level` in the MCP server, but skill docs and command routing still referenced the old names.

**How to fix:**
- Always grep plugin/ for old tool names after renaming MCP handlers

```
empathy_get_level
```

## Related Topics
- **Error**: Detailed error: MCP tool renames propagate to skill docs
