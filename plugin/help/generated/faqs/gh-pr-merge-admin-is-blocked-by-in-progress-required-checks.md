---
type: faq
name: gh-pr-merge-admin-is-blocked-by-in-progress-required-checks
tags: [testing, git]
source: .claude/CLAUDE.md
---

# FAQ: Why does gh pr merge --admin is blocked by in-progress required checks?

## Answer

The `--admin` flag only bypasses failed or missing checks — it cannot override checks that are still running. GitHub returns `Required status check "X" is in progress`.

```
Required status check "X" is in progress
```

## Related Topics
- **Error**: Detailed error: `gh pr merge --admin` is blocked by in-progress required
  checks
