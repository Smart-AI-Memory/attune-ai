---
type: faq
name: windows-ci-encoding
tags: [ci, windows, python]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Windows CI encoding?

## Answer

Windows defaults to `cp1252` which fails on any file containing non-ASCII bytes.


**Fix:**

- Always use `encoding="utf-8"` on `Path.read_text()` calls

```
encoding="utf-8"
```

## Related Topics
- **Error**: Detailed error: Windows CI encoding
