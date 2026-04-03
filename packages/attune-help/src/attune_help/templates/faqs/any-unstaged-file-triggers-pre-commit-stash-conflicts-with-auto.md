---
type: faq
name: any-unstaged-file-triggers-pre-commit-stash-conflicts-with-auto
tags: [git, claude-code, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about any unstaged file triggers pre-commit stash conflicts with auto-fix?

## Answer

Even unrelated unstaged files (e.g. `uv.lock`) cause pre-commit to stash/restore.

**How to fix:**
- before committing, either `git add` all unstaged files or `git stash push` them manually
- Running `uv run black` and `uv run ruff check --fix` on staged files beforehand doesn't help if pre-commit still detects unstaged files to stash

```
 all unstaged files or
```

## Related Topics
- **Error**: Detailed error: Any unstaged file triggers pre-commit stash conflicts with
  auto-fix
