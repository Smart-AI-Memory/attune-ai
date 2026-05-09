---
type: error
name: git-rebase-root-exec-git-commit-amend-no-edit-s-re-signs-every
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: `git rebase --root --exec "git commit --amend --no-edit
  -S"` re-signs every commit in a new repo

## Signature

`git rebase --root --exec "git commit --amend --no-edit
  -S"` re-signs every commit in a new repo

## Root Cause

When a repo is initialized with `commit.gpgsign=false` for any reason (or earlier commits used `-c commit.gpgsign=false` to bypass signing), this one-liner walks all commits from the root and re-signs each in place. Works in non-interactive terminals (no editor needed). Useful when fixing signing before first-time push of a fresh sibling repo.

## Resolution

1. Useful when fixing signing before first-time push of a fresh sibling repo

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `git rebase --root --exec "git commit --amend --no-edit
  -S"` re-signs every commit in a new repo
