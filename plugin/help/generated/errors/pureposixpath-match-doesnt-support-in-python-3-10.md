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

`PurePosixPath("a/b/c.py").match("a/**")` returns `False` because `match()` treats `*` as single-segment only (no recursive globbing). Do NOT replace `**` with `*` in `fnmatch.fnmatch()` — fnmatch's `*` matches `/`, so `src/attune/*` incorrectly matches `src/attune-redis/foo.py`. Instead, convert globs to regex: map `**` → `.*`, `*` → `[^/]*`, `?` → `[^/]`, then use `re.fullmatch()`. See `_glob_match()` in `help/manifest.py`.

## Resolution

1. `PurePosixPath("a/b/c.py").match("a/**")` returns `False` because `match()` treats `*` as single-segment only (no recursive globbing)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: `PurePosixPath.match()` doesn't support `**` in Python 3.10
- Tip: Best practice: `PurePosixPath.match()` doesn't support `**` in Python 3.10
