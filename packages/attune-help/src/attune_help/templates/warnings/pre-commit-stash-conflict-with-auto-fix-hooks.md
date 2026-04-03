---
type: warning
name: pre-commit-stash-conflict-with-auto-fix-hooks
confidence: Verified
tags: [git, claude-code, python]
source: .claude/CLAUDE.md
---

# Warning: Pre-commit stash conflict with auto-fix hooks

## Condition

When black/ruff auto-fix staged files and there are also unstaged changes, the pre-commit stash/restore cycle conflicts with the fixes

## Risk

When black/ruff auto-fix staged files and there are also unstaged changes, the pre-commit stash/restore cycle conflicts with the fixes

## Mitigation

1. run `uv run ruff check --fix <paths>` manually before committing so the staged files are already clean when the hook runs

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Pre-commit stash conflict with auto-fix hooks
