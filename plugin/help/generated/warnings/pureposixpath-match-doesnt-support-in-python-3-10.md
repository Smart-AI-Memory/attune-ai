---
type: warning
name: pureposixpath-match-doesnt-support-in-python-3-10
confidence: Verified
tags: [python]
source: .claude/CLAUDE.md
---

# Warning: `PurePosixPath.match()` doesn't support `**` in Python 3.10

## Condition

`PurePosixPath("a/b/c.py").match("a/**")` returns `False` because `match()` treats `*` as single-segment only (no recursive globbing)

## Risk

Ignoring this guidance may cause: `PurePosixPath.match()` doesn't support `**` in Python 3.10

## Mitigation

1. `PurePosixPath("a/b/c.py").match("a/**")` returns `False` because `match()` treats `*` as single-segment only (no recursive globbing)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `PurePosixPath.match()` doesn't support `**` in Python 3.10
