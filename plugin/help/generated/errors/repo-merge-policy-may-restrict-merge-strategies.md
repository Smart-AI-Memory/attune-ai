---
type: error
name: repo-merge-policy-may-restrict-merge-strategies
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: Repo merge policy may restrict merge strategies

## Signature

Repo merge policy may restrict merge strategies

## Root Cause

`gh pr merge --merge` failed with "Merge method merge commits are not allowed". This repo only allows squash merges. Always use `--squash` for `gh pr merge` in this repo.

## Resolution

1. Always use `--squash` for `gh pr merge` in this repo

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Repo merge policy may restrict merge strategies
