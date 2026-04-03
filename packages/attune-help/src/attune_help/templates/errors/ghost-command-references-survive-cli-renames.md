---
type: error
name: ghost-command-references-survive-cli-renames
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Error: Ghost command references survive CLI renames

## Signature

Ghost command references survive CLI renames

## Root Cause

Renaming `empathy` → `attune` left 30+ stale command references in discovery tips, workflow output, template definitions, and docstrings across 15 files. After any CLI rename, grep the entire `src/` for the old name and add a validation test that checks user-facing command strings against the actual registered CLI subcommands.

## Resolution

1. Renaming `empathy` → `attune` left 30+ stale command references in discovery tips, workflow output, template definitions, and docstrings across 15 files

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Ghost command references survive CLI renames
- Task: Update test mocks and assertions
