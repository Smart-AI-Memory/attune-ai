---
type: warning
name: any-unstaged-file-triggers-pre-commit-stash-conflicts-with-auto
confidence: Verified
tags: [git, claude-code, python]
source: .claude/CLAUDE.md
---

# Warning: Any unstaged file triggers pre-commit stash conflicts with
  auto-fix

## Condition

Even unrelated unstaged files (e.g

## Risk

If auto-fix hooks modify staged files during the stash, the restore conflicts and rolls back the fixes — creating an infinite fail loop

## Mitigation

1. before committing, either `git add` all unstaged files or `git stash push` them manually
2. Running `uv run black` and `uv run ruff check --fix` on staged files beforehand doesn't help if pre-commit still detects unstaged files to stash

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Any unstaged file triggers pre-commit stash conflicts with
  auto-fix
