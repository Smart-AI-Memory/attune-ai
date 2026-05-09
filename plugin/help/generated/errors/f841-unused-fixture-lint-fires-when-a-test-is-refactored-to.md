---
type: error
name: f841-unused-fixture-lint-fires-when-a-test-is-refactored-to
confidence: Verified
tags: [testing, git, python]
source: .claude/CLAUDE.md
---

# Error: F841 unused-fixture lint fires when a test is
  refactored to assert on a helper

## Signature

F841 unused-fixture lint fires when a test is
  refactored to assert on a helper

## Root Cause

Building a test with `corpus = FakeCorpus([...])` then changing the assertion to call `_stem(...)` directly leaves the `corpus` variable unused. Ruff catches this; local `pytest` doesn't. Always run `uv run python -m ruff check tests/` before pushing test-refactor commits to avoid a CI-only failure across the whole matrix.

## Resolution

1. Always run `uv run python -m ruff check tests/` before pushing test-refactor commits to avoid a CI-only failure across the whole matrix

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: F841 unused-fixture lint fires when a test is
  refactored to assert on a helper
- Tip: Best practice: F841 unused-fixture lint fires when a test is
  refactored to assert on a helper
- Task: Update test mocks and assertions
