---
type: faq
name: pureposixpath-match-doesnt-support-in-python-3-10
tags: [python]
source: .claude/CLAUDE.md
---

# FAQ: Why purePosixPath.match() doesn't support ** in Python 3.10?

## Answer

`PurePosixPath("a/b/c.py").match("a/**")` returns `False` because `match()` treats `*` as single-segment only (no recursive globbing). For `**` glob patterns, convert to fnmatch: replace `**` with `*`, then use `fnmatch.fnmatch()`.

```
PurePosixPath("a/b/c.py").match("a/**")
```

## Related Topics
- **Error**: Detailed error: `PurePosixPath.match()` doesn't support `**` in Python 3.10
