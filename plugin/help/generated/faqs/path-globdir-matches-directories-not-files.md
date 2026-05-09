---
type: faq
name: path-globdir-matches-directories-not-files
tags: [python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about path.glob("dir/**") matches directories, not files?

## Answer

The `**` pattern in `Path.glob()` matches directory entries only. To match files recursively, use `dir/**/*`.

```
 pattern in
```

## Related Topics
- **Error**: Detailed error: `Path.glob("dir/**")` matches directories, not files
