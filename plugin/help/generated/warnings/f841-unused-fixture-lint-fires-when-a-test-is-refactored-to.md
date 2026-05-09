---
type: warning
name: f841-unused-fixture-lint-fires-when-a-test-is-refactored-to
confidence: Verified
tags: [testing, git, python]
source: .claude/CLAUDE.md
---

# Warning: F841 unused-fixture lint fires when a test is
  refactored to assert on a helper

## Condition

Building a test with `corpus = FakeCorpus([...])` then changing the assertion to call `_stem(...)` directly leaves the `corpus` variable unused

## Risk

Always run `uv run python -m ruff check tests/` before pushing test-refactor commits to avoid a CI-only failure across the whole matrix

## Mitigation

1. Always run `uv run python -m ruff check tests/` before pushing test-refactor commits to avoid a CI-only failure across the whole matrix

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: F841 unused-fixture lint fires when a test is
  refactored to assert on a helper
