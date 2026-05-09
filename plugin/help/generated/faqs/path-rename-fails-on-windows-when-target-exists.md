---
type: faq
name: path-rename-fails-on-windows-when-target-exists
tags: [ci, windows, macos, python]
source: .claude/CLAUDE.md
---

# FAQ: Why do I get `FileExistsError` (path.rename() fails on Windows when target exists)?

## Answer

On Linux/macOS, `Path.rename()` atomically overwrites the target. On Windows, it raises `FileExistsError` if the target already exists.

**How to fix:**
- Use `Path.replace()` instead — it works cross-platform

```
Path.rename()
```

## Related Topics
- **Error**: Detailed error: `Path.rename()` fails on Windows when target exists
