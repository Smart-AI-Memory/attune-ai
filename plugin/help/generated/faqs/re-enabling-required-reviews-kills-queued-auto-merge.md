---
type: faq
name: re-enabling-required-reviews-kills-queued-auto-merge
tags: [git]
source: CLAUDE.md Lessons Learned
---

# FAQ: What do I need to know about: Re-enabling required reviews kills queued auto-merge?

## Answer

If you set `gh pr merge --auto` while reviews are removed, then re-enable `required_approving_review_count: 1` before the merge fires, auto-merge is blocked (no approval exists).


**Fix:**

- either wait for auto-merge to complete before re-enabling reviews, or skip auto-merge entirely and use the remove-reviews → admin-merge → re-enable-reviews pattern

```
gh pr merge --auto
```

## Related Topics
- **Error**: Detailed error: Re-enabling required reviews kills queued auto-merge
