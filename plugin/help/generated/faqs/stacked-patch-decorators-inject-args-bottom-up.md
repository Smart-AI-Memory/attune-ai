---
type: faq
name: stacked-patch-decorators-inject-args-bottom-up
tags: [testing, imports]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Stacked `@patch` decorators inject args bottom-up?

## Answer

When a test has `@patch("A") @patch("B") def test(self, mock_b, mock_a)`, the innermost (bottom) decorator's mock is the first positional arg. Forgetting a decorator while referencing its mock variable causes `NameError` at runtime, not import time.


**Fix:**

- Always count decorators vs method params

```
@patch("A") @patch("B") def test(self, mock_b, mock_a)
```

## Related Topics
- **Error**: Detailed error: Stacked `@patch` decorators inject args bottom-up
