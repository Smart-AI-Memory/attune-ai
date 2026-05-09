---
type: error
name: re-export-accessibility-tests-are-scattered-across-batch-files
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Error: Re-export accessibility tests are scattered across batch files

## Signature

Re-export accessibility tests are scattered across batch files

## Root Cause

Tests like `test_format_code_review_report_accessible` appear in SDK agent tests, workflow tests, and coverage batch files. A single re-export removal can cascade through 5+ test files. After removing any re-export, run `pytest -x` iteratively — each failure reveals the next test file to fix.

## Resolution

1. Tests like `test_format_code_review_report_accessible` appear in SDK agent tests, workflow tests, and coverage batch files

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
