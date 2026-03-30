---
type: faq
name: pre-commit-stash-conflict-when-black-ruff-fix-files-with
tags: [git, claude-code, python]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Pre-commit stash conflict when black/ruff fix files with unstaged
  siblings?

## Answer

When staging a subset of changed files and running `git commit`, pre-commit stashes unstaged changes, auto-fixes staged files, then tries to restore — causing a conflict if the same file has both staged and unstaged changes.


**Fix:**

- run `uv run ruff check --fix <files>` and `uv run black <files>` manually before staging, so the hook sees already-clean files

```
git commit
```

## Related Topics
- **Error**: Detailed error: Pre-commit stash conflict when black/ruff fix files with unstaged
  siblings
