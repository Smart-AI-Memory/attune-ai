---
type: faq
name: b904-raise-x-from-e-is-not-auto-fixable-by-ruff
tags: [python]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: B904 (`raise X from e`) is not auto-fixable by ruff?

## Answer

Despite `ruff check --fix`, B904 violations require manual edits. After fixing all violations, remove B904 from the ruff ignore list to enforce going forward.


**Fix:**

- Use `from e` when the exception variable is captured, `from None` when suppressing the original

```
ruff check --fix
```

## Related Topics
- **Error**: Detailed error: B904 (`raise X from e`) is not auto-fixable by ruff
