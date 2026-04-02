---
type: warning
name: stacked-patch-decorators-inject-args-bottom-up
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Warning: Stacked `@patch` decorators inject args bottom-up

## Condition

When a test has `@patch("A") @patch("B") def test(self, mock_b, mock_a)`, the innermost (bottom) decorator's mock is the first positional arg

## Risk

Forgetting a decorator while referencing its mock variable causes `NameError` at runtime, not import time

## Mitigation

1. Always count decorators vs method params

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Stacked `@patch` decorators inject args bottom-up
