---
type: error
name: deep-review-false-positives-verify-before-acting
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Error: Deep review false positives — verify before acting

## Signature

Deep review false positives — verify before acting

## Root Cause

The quality pass reported `summary_index.py` at 0% coverage and `test_runner_helpers.py` missing docstrings. Both were wrong — `summary_index.py` had 25 tests in `tests/memory/`, and all helpers had docstrings. Always re-verify agent findings against the actual codebase before planning fixes.

## Resolution

1. Always re-verify agent findings against the actual codebase before planning fixes

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Deep review false positives — verify before acting
- Task: Update test mocks and assertions
