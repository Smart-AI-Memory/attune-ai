---
type: warning
name: chicken-and-egg-for-optional-extras-in-dev
confidence: Verified
tags: [ci, testing, imports, packaging]
source: .claude/CLAUDE.md
---

# Warning: Chicken-and-egg for optional extras in [dev]

## Condition

If you want `pkg>=X,<Y` in `[dev]` extra so CI tests actually exercise the code paths (rather than `pytest.importorskip` and skip silently), the package MUST be resolvable — i.e., on PyPI, or the workspace source exists in the CI checkout

## Risk

If you want `pkg>=X,<Y` in `[dev]` extra so CI tests actually exercise the code paths (rather than `pytest.importorskip` and skip silently), the package MUST be resolvable — i.e., on PyPI, or the workspace source exists in the CI checkout

## Mitigation

1. Before publish, rag tests use `importorskip` and patch coverage reports 0% for the new code

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Chicken-and-egg for optional extras in [dev]
