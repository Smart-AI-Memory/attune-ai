---
type: error
name: re-enabling-required-reviews-kills-queued-auto-merge
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: Re-enabling required reviews kills queued auto-merge

## Signature

Re-enabling required reviews kills queued auto-merge

## Root Cause

If you set `gh pr merge --auto` while reviews are removed, then re-enable `required_approving_review_count: 1` before the merge fires, auto-merge is blocked (no approval exists).

## Resolution

1. either wait for auto-merge to complete before re-enabling reviews, or skip auto-merge entirely and use the remove-reviews → admin-merge → re-enable-reviews pattern

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Re-enabling required reviews kills queued auto-merge
