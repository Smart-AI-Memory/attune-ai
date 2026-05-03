---
name: re-enabling-required-reviews-kills-queued-auto-merge
source: .claude/CLAUDE.md
summary: This template explains why queuing an auto-merge with disabled required reviews
  and then re-enabling those reviews before the merge completes causes the auto-merge
  to be cancelled, and provides two workaround approaches.
tags:
- git
type: faq
---

# FAQ: Re-enabling Required Reviews Cancels Queued Auto-Merge

## Answer

If you queue a pull request for auto-merge with `gh pr merge --auto` while required reviews are disabled, then re-enable `required_approving_review_count: 1` before the merge completes, the auto-merge will be blocked — no approval exists to satisfy the newly enforced requirement.

**How to fix:**

Choose one of the following approaches:

- **Wait it out:** Allow the queued auto-merge to complete *before* re-enabling required reviews.
- **Use the manual admin pattern:** Skip auto-merge entirely and follow the remove-reviews → admin-merge → re-enable-reviews sequence instead.

```bash
gh pr merge --auto
```

> **Note:** Re-enabling branch protection rules takes effect immediately. Any queued auto-merge that no longer meets the updated requirements will be cancelled.

## Related Topics

- **Error Reference:** Re-enabling required reviews cancels queued auto-merge
