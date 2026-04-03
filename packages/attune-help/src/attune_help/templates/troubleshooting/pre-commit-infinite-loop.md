---
type: troubleshooting
name: pre-commit-infinite-loop
tags: [git, python, ci]
source: CLAUDE.md Lessons Learned
---

# Troubleshooting: Pre-commit hooks fail in a loop

## Symptom

Git commit fails repeatedly with black/ruff auto-fix, even after re-staging.

## Diagnosis

1. Check for unstaged tracked files: `git status`
2. Look for stash conflicts: pre-commit stashes unstaged changes before running hooks
3. Verify black/ruff are formatting the staged files: `uv run black --check <files>`

## Fix

Stash or add ALL unstaged tracked files before committing: `git stash push -- <unstaged files>`, then commit, then `git stash pop`.

## Prevention

Run `uv run ruff check --fix <files> && uv run black <files>` before staging. Commit with no unstaged tracked files.

## Related Topics
- **Error**: Pre-commit stash conflict with auto-fix hooks
- **Warning**: Any unstaged file triggers pre-commit stash conflicts
