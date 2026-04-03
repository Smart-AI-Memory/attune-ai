---
type: warning
name: pre-commit-stash-conflict-when-black-ruff-fix-files-with
confidence: Verified
tags: [git, claude-code, python]
source: .claude/CLAUDE.md
---

# Warning: Pre-commit stash conflict when black/ruff fix files with unstaged
  siblings

## Condition

When staging a subset of changed files and running `git commit`, pre-commit stashes unstaged changes, auto-fixes staged files, then tries to restore — causing a conflict if the same file has both staged and unstaged changes

## Risk

When staging a subset of changed files and running `git commit`, pre-commit stashes unstaged changes, auto-fixes staged files, then tries to restore — causing a conflict if the same file has both staged and unstaged changes

## Mitigation

1. run `uv run ruff check --fix <files>` and `uv run black <files>` manually before staging, so the hook sees already-clean files

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Pre-commit stash conflict when black/ruff fix files with unstaged
  siblings
