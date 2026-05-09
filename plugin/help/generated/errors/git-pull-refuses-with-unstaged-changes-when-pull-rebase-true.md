---
type: error
name: git-pull-refuses-with-unstaged-changes-when-pull-rebase-true
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: `git pull` refuses with unstaged changes when
  `pull.rebase=true`

## Signature

`git pull` refuses with unstaged changes when
  `pull.rebase=true`

## Root Cause

This repo's git config sets `pull.rebase=true`, so `git pull` invokes rebase, which fails immediately if the working tree has any unstaged changes — even if those changes don't conflict with the incoming commits. Workaround: `git fetch origin main` followed by `git merge --ff-only origin/main`. The fast-forward merge succeeds with a dirty tree because it doesn't replay any commits, just moves the branch pointer. Useful when local main is strictly behind origin/main and you have unrelated in-flight work.

## Resolution

1. Useful when local main is strictly behind origin/main and you have unrelated in-flight work

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: `git pull` refuses with unstaged changes when
  `pull.rebase=true`
- Tip: Best practice: `git pull` refuses with unstaged changes when
  `pull.rebase=true`
