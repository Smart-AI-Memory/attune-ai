---
type: error
name: pre-commit-stash-conflicts-when-any-tracked-unstaged-file
confidence: Verified
tags: [testing, git, claude-code, python]
source: .claude/CLAUDE.md
---

# Error: Pre-commit stash conflicts when any tracked unstaged file
  exists alongside staged files

## Signature

Pre-commit stash conflicts when any tracked unstaged file
  exists alongside staged files

## Root Cause

Even a single unrelated unstaged tracked file (e.g. `memdocs_storage/test_key.json`) triggers pre-commit's stash/restore cycle. If auto-fix hooks (black, ruff) modify staged files during that cycle, the restore conflicts and the commit fails.

## Resolution

1. `git stash push` the unstaged tracked files before committing, then `git stash pop` after

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
