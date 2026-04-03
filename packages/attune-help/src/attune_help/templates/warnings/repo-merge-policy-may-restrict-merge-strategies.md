---
type: warning
name: repo-merge-policy-may-restrict-merge-strategies
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: Repo merge policy may restrict merge strategies

## Condition

`gh pr merge --merge` failed with "Merge method merge commits are not allowed"

## Risk

`gh pr merge --merge` failed with "Merge method merge commits are not allowed"

## Mitigation

1. Always use `--squash` for `gh pr merge` in this repo

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Repo merge policy may restrict merge strategies
