---
type: faq
name: read-source-before-writing-tests-for-tricky-logic
tags: [testing]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Read source before writing tests for tricky logic?

## Answer

The inline- comment check in `is_in_docstring_or_comment()` uses a ternary that defaults to `True` for any line not containing `eval`. Tests written against assumed behavior (expected `False`) failed.


**Fix:**

- Always read the actual implementation before asserting expected values for non-obvious control flow

```
is_in_docstring_or_comment()
```

## Related Topics
- **Error**: Detailed error: Read source before writing tests for tricky logic
