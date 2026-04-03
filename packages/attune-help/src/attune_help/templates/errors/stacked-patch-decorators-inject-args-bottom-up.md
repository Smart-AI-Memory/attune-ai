---
type: error
name: stacked-patch-decorators-inject-args-bottom-up
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Error: Stacked `@patch` decorators inject args bottom-up

## Signature

NameError

## Root Cause

When a test has `@patch("A") @patch("B") def test(self, mock_b, mock_a)`, the innermost (bottom) decorator's mock is the first positional arg. Forgetting a decorator while referencing its mock variable causes `NameError` at runtime, not import time. Always count decorators vs method params.

## Resolution

1. Always count decorators vs method params

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Stacked `@patch` decorators inject args bottom-up
- Task: Update test mocks and assertions
