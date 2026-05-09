---
type: faq
name: git-rebase-root-exec-git-commit-amend-no-edit-s-re-signs-every
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about git rebase --root --exec "git commit --amend --no-edit -S" re-signs every commit in a new repo?

## Answer

When a repo is initialized with `commit.gpgsign=false` for any reason (or earlier commits used `-c commit.gpgsign=false` to bypass signing), this one-liner walks all commits from the root and re-signs each in place. Works in non-interactive terminals (no editor needed).

**How to fix:**
- Useful when fixing signing before first-time push of a fresh sibling repo

```
commit.gpgsign=false
```

## Related Topics
- **Error**: Detailed error: `git rebase --root --exec "git commit --amend --no-edit
  -S"` re-signs every commit in a new repo
