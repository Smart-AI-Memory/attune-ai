---
type: error
name: pull-main-before-merging-develop-to-avoid-merge-commits
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: Pull `main` before merging `develop` to avoid merge commits

## Signature

Pull `main` before merging `develop` to avoid merge commits

## Root Cause

If `origin/main` has commits not in local `main`, merging `develop` creates a merge commit. Always `git pull origin main` first, then `git merge develop`. This also avoids the GitHub "no merge commits" rule violation.

## Resolution

1. Always `git pull origin main` first, then `git merge develop`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Pull `main` before merging `develop` to avoid merge commits
- Tip: Best practice: Pull `main` before merging `develop` to avoid merge commits
