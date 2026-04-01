---
type: error
name: plugin-read-skill-references-break-outside-the-plugin
confidence: Verified
tags: [claude-code, packaging]
source: .claude/CLAUDE.md
---

# Error: Plugin `Read skill` references break outside the plugin

## Signature

Plugin `Read skill` references break outside the plugin

## Root Cause

The `file:///skills/doc-gen/SKILL.md` path in plugin commands is relative to `${CLAUDE_PLUGIN_ROOT}`. When the command is copied to `~/.claude/commands/` via `attune setup`, the path doesn't resolve. Commands shipped in `src/attune/commands/` (for PyPI) must be self-contained — embed the instructions directly instead of referencing skill files.

## Resolution

1. The `file:///skills/doc-gen/SKILL.md` path in plugin commands is relative to `${CLAUDE_PLUGIN_ROOT}`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
