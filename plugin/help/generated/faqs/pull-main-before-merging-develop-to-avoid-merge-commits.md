---
type: faq
name: pull-main-before-merging-develop-to-avoid-merge-commits
tags: [git]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Pull `main` before merging `develop` to avoid merge commits?

## Answer

If `origin/main` has commits not in local `main`, merging `develop` creates a merge commit. This also avoids the GitHub "no merge commits" rule violation.


**Fix:**

- Always `git pull origin main` first, then `git merge develop`

```
origin/main
```

## Related Topics
- **Error**: Detailed error: Pull `main` before merging `develop` to avoid merge commits
