---
type: error
name: pre-commit-stash-conflict-with-auto-fix-hooks
confidence: Verified
tags: [git, claude-code, python]
source: .claude/CLAUDE.md
---

# Error: Pre-commit stash conflict with auto-fix hooks

## Signature

Pre-commit stash conflict with auto-fix hooks

## Root Cause

When black/ruff auto-fix staged files and there are also unstaged changes, the pre-commit stash/restore cycle conflicts with the fixes.

## Resolution

1. run `uv run ruff check --fix <paths>` manually before committing so the staged files are already clean when the hook runs

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
