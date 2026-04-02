---
type: error
name: shadow-directories-at-repo-root-break-imports
confidence: Verified
tags: [imports]
source: .claude/CLAUDE.md
---

# Error: Shadow directories at repo root break imports

## Signature

ModuleNotFoundError

## Root Cause

An `attune/` directory at the repo root (from prototyping) shadows the installed `src/attune/` package, causing `ModuleNotFoundError` on submodules that only exist in one copy. Always check for rogue top-level directories matching the package name before debugging import errors.

## Resolution

1. Always check for rogue top-level directories matching the package name before debugging import errors

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Shadow directories at repo root break imports
