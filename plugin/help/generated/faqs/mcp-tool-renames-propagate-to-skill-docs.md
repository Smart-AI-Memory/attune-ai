---
type: faq
name: mcp-tool-renames-propagate-to-skill-docs
tags: [claude-code]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: MCP tool renames propagate to skill docs?

## Answer

The empathy tools were renamed from `empathy_get_level`/`empathy_set_level` to `attune_get_level`/`attune_set_level` in the MCP server, but skill docs and command routing still referenced the old names.


**Fix:**

- Always grep plugin/ for old tool names after renaming MCP handlers

```
empathy_get_level
```

## Related Topics
- **Error**: Detailed error: MCP tool renames propagate to skill docs
