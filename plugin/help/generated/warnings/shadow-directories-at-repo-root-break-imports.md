---
type: warning
name: shadow-directories-at-repo-root-break-imports
confidence: Verified
tags: [imports]
source: .claude/CLAUDE.md
---

# Warning: Shadow directories at repo root break imports

## Condition

An `attune/` directory at the repo root (from prototyping) shadows the installed `src/attune/` package, causing `ModuleNotFoundError` on submodules that only exist in one copy

## Risk

An `attune/` directory at the repo root (from prototyping) shadows the installed `src/attune/` package, causing `ModuleNotFoundError` on submodules that only exist in one copy

## Mitigation

1. Always check for rogue top-level directories matching the package name before debugging import errors

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Shadow directories at repo root break imports
