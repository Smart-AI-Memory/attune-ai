---
type: error
name: tests-for-optional-dep-code-need-pytest-importorskip-guards-in
confidence: Verified
tags: [ci, testing, imports]
source: .claude/CLAUDE.md
---

# Error: Tests for optional-dep code need `pytest.importorskip()`
  guards in CI

## Signature

ModuleNotFoundError

## Root Cause

Tests that import `redis`, `jinja2`, or other optional dependencies fail with `ModuleNotFoundError` in CI where only core deps are installed. Add `pytest.importorskip("redis")` at the top of the test module or use `@pytest.mark.skipif` to skip gracefully. This caused 5 failures in PR #98 (3 redis, 1 jinja2, 1 redis auto-detect).

## Resolution

1. Add `pytest.importorskip("redis")` at the top of the test module or use `@pytest.mark.skipif` to skip gracefully

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Tests for optional-dep code need `pytest.importorskip()`
  guards in CI
- Task: Update test mocks and assertions
