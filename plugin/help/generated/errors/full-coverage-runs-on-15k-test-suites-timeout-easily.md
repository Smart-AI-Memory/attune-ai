---
type: error
name: full-coverage-runs-on-15k-test-suites-timeout-easily
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Error: Full coverage runs on 15k+ test suites timeout easily

## Signature

Full coverage runs on 15k+ test suites timeout easily

## Root Cause

`pytest --cov=src/attune` with the full test suite takes 10+ minutes. For development feedback, use targeted coverage: `pytest tests/unit/module/ --cov=attune.module --no-cov-on-fail` to measure specific modules in seconds.

## Resolution

1. `pytest --cov=src/attune` with the full test suite takes 10+ minutes

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Full coverage runs on 15k+ test suites timeout easily
- Task: Update test mocks and assertions
