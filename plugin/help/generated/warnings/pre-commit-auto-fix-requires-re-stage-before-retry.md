---
type: warning
name: pre-commit-auto-fix-requires-re-stage-before-retry
confidence: Verified
tags: [git, claude-code, python]
source: .claude/CLAUDE.md
---

# Warning: Pre-commit auto-fix requires re-stage before retry

## Condition

When black/ruff auto-fix staged files during `git commit`, the commit fails but the fixes are applied to the working tree

## Risk

When black/ruff auto-fix staged files during `git commit`, the commit fails but the fixes are applied to the working tree

## Mitigation

1. When black/ruff auto-fix staged files during `git commit`, the commit fails but the fixes are applied to the working tree

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Pre-commit auto-fix requires re-stage before retry
