---
type: faq
name: git-pull-refuses-with-unstaged-changes-when-pull-rebase-true
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about git pull refuses with unstaged changes when pull.rebase=true?

## Answer

This repo's git config sets `pull.rebase=true`, so `git pull` invokes rebase, which fails immediately if the working tree has any unstaged changes — even if those changes don't conflict with the incoming commits. Workaround: `git fetch origin main` followed by `git merge --ff-only origin/main`.

**How to fix:**
- Useful when local main is strictly behind origin/main and you have unrelated in-flight work

```
pull.rebase=true
```

## Related Topics
- **Error**: Detailed error: `git pull` refuses with unstaged changes when
  `pull.rebase=true`
