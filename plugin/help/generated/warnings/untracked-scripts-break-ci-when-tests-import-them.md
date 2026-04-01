---
type: warning
name: untracked-scripts-break-ci-when-tests-import-them
confidence: Verified
tags: [ci, testing, imports, git, claude-code]
source: .claude/CLAUDE.md
---

# Warning: Untracked scripts break CI when tests import them

## Condition

The `test_sync_agents_skills.py` test imported from `scripts/sync_agents_skills.py` which existed locally but was never committed

## Risk

CI failed with `ModuleNotFoundError` on all 12 platforms

## Mitigation

1. Always `git status` scripts referenced by tests before pushing

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Untracked scripts break CI when tests import them
