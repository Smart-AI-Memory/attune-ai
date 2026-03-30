---
type: faq
name: pre-commit-stash-conflict-with-auto-fix-hooks
tags: [git, claude-code, python]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Pre-commit stash conflict with auto-fix hooks?

## Answer

When black/ruff auto-fix staged files and there are also unstaged changes, the pre-commit stash/restore cycle conflicts with the fixes.


**Fix:**

- run `uv run ruff check --fix <paths>` manually before committing so the staged files are already clean when the hook runs

```
uv run ruff check --fix <paths>
```

## Related Topics
- **Error**: Detailed error: Pre-commit stash conflict with auto-fix hooks
