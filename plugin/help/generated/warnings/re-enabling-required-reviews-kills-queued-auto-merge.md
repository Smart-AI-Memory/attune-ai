---
type: warning
name: re-enabling-required-reviews-kills-queued-auto-merge
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: Re-enabling required reviews kills queued auto-merge

## Condition

If you set `gh pr merge --auto` while reviews are removed, then re-enable `required_approving_review_count: 1` before the merge fires, auto-merge is blocked (no approval exists)

## Risk

If you set `gh pr merge --auto` while reviews are removed, then re-enable `required_approving_review_count: 1` before the merge fires, auto-merge is blocked (no approval exists)

## Mitigation

1. either wait for auto-merge to complete before re-enabling reviews, or skip auto-merge entirely and use the remove-reviews → admin-merge → re-enable-reviews pattern

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Re-enabling required reviews kills queued auto-merge
