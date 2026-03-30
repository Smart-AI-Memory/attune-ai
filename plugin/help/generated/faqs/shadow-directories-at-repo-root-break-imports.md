---
type: faq
name: shadow-directories-at-repo-root-break-imports
tags: [imports]
source: CLAUDE.md Lessons Learned
---

# FAQ: Why does Shadow directories at repo root break imports?

## Answer

An `attune/` directory at the repo root (from prototyping) shadows the installed `src/attune/` package, causing `ModuleNotFoundError` on submodules that only exist in one copy.


**Fix:**

- Always check for rogue top-level directories matching the package name before debugging import errors

```
 directory at the repo root (from prototyping) shadows the installed
```

## Related Topics
- **Error**: Detailed error: Shadow directories at repo root break imports
