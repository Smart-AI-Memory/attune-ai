---
type: faq
name: stacked-patch-decorators-inject-args-bottom-up
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# FAQ: Why do I get `NameError` (stacked @patch decorators inject args bottom-up)?

## Answer

When a test has `@patch("A") @patch("B") def test(self, mock_b, mock_a)`, the innermost (bottom) decorator's mock is the first positional arg. Forgetting a decorator while referencing its mock variable causes `NameError` at runtime, not import time.

**How to fix:**
- Always count decorators vs method params

```
@patch("A") @patch("B") def test(self, mock_b, mock_a)
```

## Related Topics
- **Error**: Detailed error: Stacked `@patch` decorators inject args bottom-up
