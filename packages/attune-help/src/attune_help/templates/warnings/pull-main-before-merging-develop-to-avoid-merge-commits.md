---
type: warning
name: pull-main-before-merging-develop-to-avoid-merge-commits
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: Pull `main` before merging `develop` to avoid merge commits

## Condition

If `origin/main` has commits not in local `main`, merging `develop` creates a merge commit

## Risk

Ignoring this guidance may cause: Pull `main` before merging `develop` to avoid merge commits

## Mitigation

1. Always `git pull origin main` first, then `git merge develop`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Pull `main` before merging `develop` to avoid merge commits
