---
type: error
name: path-globdir-matches-directories-not-files
confidence: Verified
tags: [python]
source: .claude/CLAUDE.md
---

# Error: `Path.glob("dir/**")` matches directories, not files

## Signature

`Path.glob("dir/**")` matches directories, not files

## Root Cause

The `**` pattern in `Path.glob()` matches directory entries only. To match files recursively, use `dir/**/*`. This matters when users write `src/auth/**` in config files (like `.help/features.yaml`) — the code that resolves these globs must append `/*` when the pattern ends with `**`. Discovered when `compute_source_hash()` returned 0 matched files for all 14 features until the glob was corrected.

## Resolution

1. The `**` pattern in `Path.glob()` matches directory entries only

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `Path.glob("dir/**")` matches directories, not files
