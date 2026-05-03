---
name: pre-commit-infinite-loop
source: CLAUDE.md Lessons Learned
summary: This template explains how to diagnose and resolve a pre-commit hook failure
  loop caused by conflicts between unstaged tracked files and auto-fixing tools like
  Black or Ruff, and provides prevention strategies.
tags:
- git
- python
- ci
type: troubleshooting
---

# Troubleshooting: Pre-commit Hooks Fail in a Loop

## Symptom

A `git commit` fails repeatedly even after re-staging files. The loop occurs because Black or Ruff auto-fixes staged content, but pre-commit's internal stash mechanism conflicts with unstaged changes — causing the hook to re-run and fail indefinitely.

## Diagnosis

Work through the following checks in order:

1. **Identify unstaged tracked files** — any unstaged change can trigger the conflict:
   ```bash
   git status
   ```

2. **Check for stash conflicts** — pre-commit stashes unstaged changes before running hooks; if that stash operation conflicts, the cycle begins.

3. **Confirm Black/Ruff are targeting staged content** — verify the formatter is actually checking the files you intend to commit:
   ```bash
   uv run black --check <files>
   uv run ruff check <files>
   ```

## Fix

Ensure there are no unstaged tracked files before committing. The safest approach is to stash them temporarily:

```bash
# 1. Stash unstaged changes
git stash push -- <unstaged-files>

# 2. Commit normally
git commit -m "your message"

# 3. Restore stashed changes
git stash pop
```

> **Note:** Replace `<unstaged-files>` with the specific paths shown by `git status`. Stashing untracked files is not required — only tracked files with unstaged changes cause the conflict.

## Prevention

Format and fix files **before** staging them to avoid hook failures entirely:

```bash
uv run ruff check --fix <files> && uv run black <files>
git add <files>
git commit -m "your message"
```

Always commit with a clean working tree — no unstaged changes to tracked files.

## Related Issues

| Type | Description |
|------|-------------|
| **Error** | Pre-commit stash conflict with auto-fix hooks |
| **Warning** | Any unstaged tracked file can trigger a pre-commit stash conflict |
