---
type: faq
name: tests-for-optional-dep-code-need-pytest-importorskip-guards-in
tags: [ci, testing, imports]
source: .claude/CLAUDE.md
---

# FAQ: Why do I get `ModuleNotFoundError` (tests for optional-dep code need pytest.importorskip() guards in CI)?

## Answer

Tests that import `redis`, `jinja2`, or other optional dependencies fail with `ModuleNotFoundError` in CI where only core deps are installed. Add `pytest.importorskip("redis")` at the top of the test module or use `@pytest.mark.skipif` to skip gracefully.

```
, or other optional dependencies fail with
```

## Related Topics
- **Error**: Detailed error: Tests for optional-dep code need `pytest.importorskip()`
  guards in CI
