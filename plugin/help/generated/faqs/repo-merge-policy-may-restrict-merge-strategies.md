---
type: faq
name: repo-merge-policy-may-restrict-merge-strategies
tags: [git]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Repo merge policy may restrict merge strategies?

## Answer

`gh pr merge --merge` failed with "Merge method merge commits are not allowed". This repo only allows squash merges.


**Fix:**

- Always use `--squash` for `gh pr merge` in this repo

```
gh pr merge --merge
```

## Related Topics
- **Error**: Detailed error: Repo merge policy may restrict merge strategies
