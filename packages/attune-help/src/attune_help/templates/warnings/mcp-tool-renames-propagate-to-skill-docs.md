---
type: warning
name: mcp-tool-renames-propagate-to-skill-docs
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Warning: MCP tool renames propagate to skill docs

## Condition

The empathy tools were renamed from `empathy_get_level`/`empathy_set_level` to `attune_get_level`/`attune_set_level` in the MCP server, but skill docs and command routing still referenced the old names

## Risk

Ignoring this guidance may cause: MCP tool renames propagate to skill docs

## Mitigation

1. Always grep plugin/ for old tool names after renaming MCP handlers

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: MCP tool renames propagate to skill docs
