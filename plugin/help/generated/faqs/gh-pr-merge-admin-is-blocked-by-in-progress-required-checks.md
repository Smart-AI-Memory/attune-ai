---
name: gh-pr-merge-admin-is-blocked-by-in-progress-required-checks
source: .claude/CLAUDE.md
summary: This template explains why GitHub CLI's `--admin` flag cannot bypass in-progress
  required status checks and how to resolve the issue.
tags:
- testing
- git
type: faq
---

# FAQ: Why is `gh pr merge --admin` blocked by in-progress required checks?

## Answer

The `--admin` flag bypasses required checks that have **failed** or are **missing**, but it cannot override checks that are still **in progress**. If any required status check is still running, GitHub blocks the merge and returns an error similar to the following:

```
Required status check "X" is in progress
```

To resolve this, wait for all required status checks to complete before attempting to merge with `--admin`.

## Related Topics

- **Error:** `gh pr merge --admin` is blocked by in-progress required checks
