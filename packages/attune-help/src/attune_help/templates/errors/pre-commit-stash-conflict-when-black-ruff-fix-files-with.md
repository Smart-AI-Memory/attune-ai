---
type: error
name: pre-commit-stash-conflict-when-black-ruff-fix-files-with
confidence: Verified
tags: [git, claude-code, python]
source: .claude/CLAUDE.md
---

# Error: Pre-commit stash conflict when black/ruff fix files with unstaged
  siblings

## Signature

Pre-commit stash conflict when black/ruff fix files with unstaged
  siblings

## Root Cause

When staging a subset of changed files and running `git commit`, pre-commit stashes unstaged changes, auto-fixes staged files, then tries to restore — causing a conflict if the same file has both staged and unstaged changes.

## Resolution

1. run `uv run ruff check --fix <files>` and `uv run black <files>` manually before staging, so the hook sees already-clean files

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
