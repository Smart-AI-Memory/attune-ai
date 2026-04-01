---
type: error
name: pre-commit-auto-fix-requires-re-stage-before-retry
confidence: Verified
tags: [git, claude-code, python]
source: .claude/CLAUDE.md
---

# Error: Pre-commit auto-fix requires re-stage before retry

## Signature

Pre-commit auto-fix requires re-stage before retry

## Root Cause

When black/ruff auto-fix staged files during `git commit`, the commit fails but the fixes are applied to the working tree. The files must be `git add`-ed again before retrying the commit. This is different from the stash conflict issue — here there are no unstaged siblings, just the hook modifying staged files.

## Resolution

1. When black/ruff auto-fix staged files during `git commit`, the commit fails but the fixes are applied to the working tree

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
