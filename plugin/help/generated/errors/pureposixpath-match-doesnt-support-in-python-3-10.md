---
type: error
name: pureposixpath-match-doesnt-support-in-python-3-10
confidence: Verified
tags: [python]
source: .claude/CLAUDE.md
---

# Error: `PurePosixPath.match()` doesn't support `**` in Python 3.10

## Signature

`PurePosixPath.match()` doesn't support `**` in Python 3.10

## Root Cause

`PurePosixPath("a/b/c.py").match("a/**")` returns `False` because `match()` treats `*` as single-segment only (no recursive globbing). For `**` glob patterns, convert to fnmatch: replace `**` with `*`, then use `fnmatch.fnmatch()`. Python 3.13+ adds recursive support but 3.10 does not.

## Resolution

1. `PurePosixPath("a/b/c.py").match("a/**")` returns `False` because `match()` treats `*` as single-segment only (no recursive globbing)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `PurePosixPath.match()` doesn't support `**` in Python 3.10
