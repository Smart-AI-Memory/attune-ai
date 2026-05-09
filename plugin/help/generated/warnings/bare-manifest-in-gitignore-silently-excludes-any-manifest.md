---
type: warning
name: bare-manifest-in-gitignore-silently-excludes-any-manifest
confidence: Verified
tags: [ci, testing, windows, macos]
source: .claude/CLAUDE.md
---

# Warning: Bare `MANIFEST` in `.gitignore` silently
  excludes any `manifest/` directory on
  case-insensitive filesystems

## Condition

attune-author's `.gitignore` had a plain `MANIFEST` entry intended for setuptools' `MANIFEST` artifact

## Risk

Local tests passed; Linux CI failed with "missing template dir for feature 'manifest'" across 9 assertions

## Mitigation

1. scope setuptools patterns to repo root (`/MANIFEST`, `/MANIFEST.in`)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Bare `MANIFEST` in `.gitignore` silently
  excludes any `manifest/` directory on
  case-insensitive filesystems
