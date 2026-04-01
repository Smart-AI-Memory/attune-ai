---
type: error
name: any-unstaged-file-triggers-pre-commit-stash-conflicts-with-auto
confidence: Verified
tags: [git, claude-code, python]
source: .claude/CLAUDE.md
---

# Error: Any unstaged file triggers pre-commit stash conflicts with
  auto-fix

## Signature

Any unstaged file triggers pre-commit stash conflicts with
  auto-fix

## Root Cause

Even unrelated unstaged files (e.g. `uv.lock`) cause pre-commit to stash/restore. If auto-fix hooks modify staged files during the stash, the restore conflicts and rolls back the fixes — creating an infinite fail loop.

## Resolution

1. before committing, either `git add` all unstaged files or `git stash push` them manually
2. Running `uv run black` and `uv run ruff check --fix` on staged files beforehand doesn't help if pre-commit still detects unstaged files to stash

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Any unstaged file triggers pre-commit stash conflicts with
  auto-fix
