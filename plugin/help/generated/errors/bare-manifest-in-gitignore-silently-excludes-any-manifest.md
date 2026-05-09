---
type: error
name: bare-manifest-in-gitignore-silently-excludes-any-manifest
confidence: Verified
tags: [ci, testing, windows, macos]
source: .claude/CLAUDE.md
---

# Error: Bare `MANIFEST` in `.gitignore` silently
  excludes any `manifest/` directory on
  case-insensitive filesystems

## Signature

Bare `MANIFEST` in `.gitignore` silently
  excludes any `manifest/` directory on
  case-insensitive filesystems

## Root Cause

attune-author's `.gitignore` had a plain `MANIFEST` entry intended for setuptools' `MANIFEST` artifact. Combined with git's default case-insensitive matching on macOS/Windows, it also excluded the `.help/templates/manifest/` directory — 11 polished template files that existed locally but were never tracked. Local tests passed; Linux CI failed with "missing template dir for feature 'manifest'" across 9 assertions.

## Resolution

1. scope setuptools patterns to repo root (`/MANIFEST`, `/MANIFEST.in`)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Bare `MANIFEST` in `.gitignore` silently
  excludes any `manifest/` directory on
  case-insensitive filesystems
- Task: Update test mocks and assertions
