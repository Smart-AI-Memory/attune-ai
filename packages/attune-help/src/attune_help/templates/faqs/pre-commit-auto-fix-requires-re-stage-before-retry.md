---
type: faq
name: pre-commit-auto-fix-requires-re-stage-before-retry
tags: [git, claude-code, python]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about pre-commit auto-fix requires re-stage before retry?

## Answer

When black/ruff auto-fix staged files during `git commit`, the commit fails but the fixes are applied to the working tree. The files must be `git add`-ed again before retrying the commit.

```
git commit
```

## Related Topics
- **Error**: Detailed error: Pre-commit auto-fix requires re-stage before retry
