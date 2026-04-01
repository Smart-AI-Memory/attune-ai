---
type: faq
name: repo-merge-policy-may-restrict-merge-strategies
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about repo merge policy may restrict merge strategies?

## Answer

`gh pr merge --merge` failed with "Merge method merge commits are not allowed". This repo only allows squash merges.

**How to fix:**
- Always use `--squash` for `gh pr merge` in this repo

```
gh pr merge --merge
```

## Related Topics
- **Error**: Detailed error: Repo merge policy may restrict merge strategies
