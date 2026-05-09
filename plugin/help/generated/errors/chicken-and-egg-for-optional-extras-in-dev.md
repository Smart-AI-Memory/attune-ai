---
type: error
name: chicken-and-egg-for-optional-extras-in-dev
confidence: Verified
tags: [ci, testing, imports, packaging]
source: .claude/CLAUDE.md
---

# Error: Chicken-and-egg for optional extras in [dev]

## Signature

Chicken-and-egg for optional extras in [dev]

## Root Cause

If you want `pkg>=X,<Y` in `[dev]` extra so CI tests actually exercise the code paths (rather than `pytest.importorskip` and skip silently), the package MUST be resolvable — i.e., on PyPI, or the workspace source exists in the CI checkout. Publishing the package is the unblocker when you're working in the monorepo-sibling pattern where CI doesn't have the sibling checkout. Sequence: publish 0.1.0 → add to `[dev]` → tests run → coverage lands. Before publish, rag tests use `importorskip` and patch coverage reports 0% for the new code.

## Resolution

1. If you want `pkg>=X,<Y` in `[dev]` extra so CI tests actually exercise the code paths (rather than `pytest.importorskip` and skip silently), the package MUST be resolvable — i.e., on PyPI, or the workspace source exists in the CI checkout

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Chicken-and-egg for optional extras in [dev]
- Task: Update test mocks and assertions
