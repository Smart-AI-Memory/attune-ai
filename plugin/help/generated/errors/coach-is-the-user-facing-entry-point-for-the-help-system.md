---
type: error
name: coach-is-the-user-facing-entry-point-for-the-help-system
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: `/coach` is the user-facing entry point for the `.help`
  system

## Signature

`/coach` is the user-facing entry point for the `.help`
  system

## Root Cause

The skill was renamed from `/help` to `/coach` because Claude Code's built-in `/help` command shadows plugin skills. `/coach` routes to the `.help` system via MCP tools (`help_lookup`, `help_init`, `help_status`, `help_update`, `help_maintain`). The old `/help` skill still exists but is for quick command reference only — `/coach` is the one that connects to `.help/features.yaml`, staleness detection, and template generation.

## Resolution

1. The skill was renamed from `/help` to `/coach` because Claude Code's built-in `/help` command shadows plugin skills

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `/coach` is the user-facing entry point for the `.help`
  system
