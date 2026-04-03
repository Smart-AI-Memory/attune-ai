---
type: warning
name: pre-commit-stash-conflicts-when-any-tracked-unstaged-file
confidence: Verified
tags: [testing, git, claude-code, python]
source: .claude/CLAUDE.md
---

# Warning: Pre-commit stash conflicts when any tracked unstaged file
  exists alongside staged files

## Condition

Even a single unrelated unstaged tracked file (e.g

## Risk

If auto-fix hooks (black, ruff) modify staged files during that cycle, the restore conflicts and the commit fails

## Mitigation

1. `git stash push` the unstaged tracked files before committing, then `git stash pop` after

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Pre-commit stash conflicts when any tracked unstaged file
  exists alongside staged files
