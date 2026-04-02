---
type: faq
name: pre-commit-black-unstaged-files-re-stage-after-failure
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: Why does pre-commit black + unstaged files: re-stage after failure?

## Answer

When `git commit` fails because black reformatted staged files, the reformatted files are in the working tree but unstaged. This is distinct from the stash conflict issue — here the hook succeeds at formatting but the commit is rejected because files changed.

**How to fix:**
- Run `git add <files>` again before retrying the commit

```
git commit
```

## Related Topics
- **Error**: Detailed error: Pre-commit black + unstaged files: re-stage after failure
