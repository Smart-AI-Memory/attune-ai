---
type: warning
name: path-globdir-matches-directories-not-files
confidence: Verified
tags: [python]
source: .claude/CLAUDE.md
---

# Warning: `Path.glob("dir/**")` matches directories, not files

## Condition

The `**` pattern in `Path.glob()` matches directory entries only

## Risk

Ignoring this guidance may cause: `Path.glob("dir/**")` matches directories, not files

## Mitigation

1. The `**` pattern in `Path.glob()` matches directory entries only

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `Path.glob("dir/**")` matches directories, not files
