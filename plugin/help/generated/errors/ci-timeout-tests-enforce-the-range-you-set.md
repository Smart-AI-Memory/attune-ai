---
type: error
name: ci-timeout-tests-enforce-the-range-you-set
confidence: Verified
tags: [ci, testing]
source: .claude/CLAUDE.md
---

# Error: CI timeout tests enforce the range you set

## Signature

CI timeout tests enforce the range you set

## Root Cause

The test `test_timeout_values_are_reasonable` in `tests/unit/ci/` asserts that all workflow job timeouts fall within an allowed range. When bumping `timeout-minutes` in a workflow YAML, also update the test's upper bound or it fails on every platform.

## Resolution

1. The test `test_timeout_values_are_reasonable` in `tests/unit/ci/` asserts that all workflow job timeouts fall within an allowed range

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
