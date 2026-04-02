---
type: warning
name: test-mocks-must-match-imports
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Warning: Test mocks must match imports

## Condition

When a function changes its import path, all test mocks must be updated to match or side effects are silently ignored and assertions fail

## Risk

When a function changes its import path, all test mocks must be updated to match or side effects are silently ignored and assertions fail

## Mitigation

1. When a function changes its import path, all test mocks must be updated to match or side effects are silently ignored and assertions fail

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Test mocks must match imports
