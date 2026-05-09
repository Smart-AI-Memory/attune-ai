---
type: faq
name: f841-unused-fixture-lint-fires-when-a-test-is-refactored-to
tags: [testing, git, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about F841 unused-fixture lint fires when a test is refactored to assert on a helper?

## Answer

Building a test with `corpus = FakeCorpus([...])` then changing the assertion to call `_stem(...)` directly leaves the `corpus` variable unused. Ruff catches this; local `pytest` doesn't.

**How to fix:**
- Always run `uv run python -m ruff check tests/` before pushing test-refactor commits to avoid a CI-only failure across the whole matrix

```
corpus = FakeCorpus([...])
```

## Related Topics
- **Error**: Detailed error: F841 unused-fixture lint fires when a test is
  refactored to assert on a helper
