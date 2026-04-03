---
type: faq
name: windows-ci-encoding
tags: [ci, windows, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about windows CI encoding?

## Answer

Windows defaults to `cp1252` which fails on any file containing non-ASCII bytes.

**How to fix:**
- Always use `encoding="utf-8"` on `Path.read_text()` calls

```
encoding="utf-8"
```

## Related Topics
- **Error**: Detailed error: Windows CI encoding
