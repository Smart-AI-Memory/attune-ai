---
name: pre-commit-stash-conflicts-when-any-tracked-unstaged-file
source: .claude/CLAUDE.md
summary: This template explains how to resolve pre-commit conflicts that occur when
  tracked files with unstaged changes are committed alongside staged files, and provides
  git stash commands to prevent the issue.
tags:
- testing
- git
- claude-code
- python
type: faq
---

# FAQ: Pre-commit stash conflicts when tracked unstaged files exist alongside staged files

## Answer

If even a single tracked file has unstaged changes (for example, `memdocs_storage/test_key.json`), pre-commit will trigger its stash/restore cycle. This can cause conflicts when other files are simultaneously staged for commit.

## Resolution

Stash your unstaged tracked files before committing, then restore them afterward:

```bash
git stash push
git commit
git stash pop
```

If you want to stash only specific files, you can target them explicitly:

```bash
git stash push memdocs_storage/test_key.json
git commit
git stash pop
```

## Related Topics

- **Error reference**: Pre-commit stash conflicts when any tracked unstaged file exists alongside staged files
