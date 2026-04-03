---
type: error
name: test-mocks-must-match-imports
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Error: Test mocks must match imports

## Signature

Test mocks must match imports

## Root Cause

When a function changes its import path, all test mocks must be updated to match or side effects are silently ignored and assertions fail.

## Resolution

1. When a function changes its import path, all test mocks must be updated to match or side effects are silently ignored and assertions fail

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
