---
type: error
name: untracked-scripts-break-ci-when-tests-import-them
confidence: Verified
tags: [ci, testing, imports, git, claude-code]
source: .claude/CLAUDE.md
---

# Error: Untracked scripts break CI when tests import them

## Signature

ModuleNotFoundError

## Root Cause

The `test_sync_agents_skills.py` test imported from `scripts/sync_agents_skills.py` which existed locally but was never committed. CI failed with `ModuleNotFoundError` on all 12 platforms. Always `git status` scripts referenced by tests before pushing. Guard with `pytest.importorskip()` for resilience.

## Resolution

1. Always `git status` scripts referenced by tests before pushing

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Untracked scripts break CI when tests import them
- Tip: Best practice: Untracked scripts break CI when tests import them
- Task: Update test mocks and assertions
