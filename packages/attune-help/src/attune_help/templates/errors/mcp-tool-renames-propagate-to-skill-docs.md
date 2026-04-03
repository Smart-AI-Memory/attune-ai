---
type: error
name: mcp-tool-renames-propagate-to-skill-docs
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: MCP tool renames propagate to skill docs

## Signature

MCP tool renames propagate to skill docs

## Root Cause

The empathy tools were renamed from `empathy_get_level`/`empathy_set_level` to `attune_get_level`/`attune_set_level` in the MCP server, but skill docs and command routing still referenced the old names. Always grep plugin/ for old tool names after renaming MCP handlers.

## Resolution

1. Always grep plugin/ for old tool names after renaming MCP handlers

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: MCP tool renames propagate to skill docs
