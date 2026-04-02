---
type: warning
name: tests-for-optional-dep-code-need-pytest-importorskip-guards-in
confidence: Verified
tags: [ci, testing, imports]
source: .claude/CLAUDE.md
---

# Warning: Tests for optional-dep code need `pytest.importorskip()`
  guards in CI

## Condition

Tests that import `redis`, `jinja2`, or other optional dependencies fail with `ModuleNotFoundError` in CI where only core deps are installed

## Risk

Tests that import `redis`, `jinja2`, or other optional dependencies fail with `ModuleNotFoundError` in CI where only core deps are installed

## Mitigation

1. Add `pytest.importorskip("redis")` at the top of the test module or use `@pytest.mark.skipif` to skip gracefully

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Tests for optional-dep code need `pytest.importorskip()`
  guards in CI
