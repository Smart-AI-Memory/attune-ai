---
type: error
name: macos-var-private-var-symlink-breaks-path-assertions
confidence: Verified
tags: [testing, security, windows, macos, python]
source: .claude/CLAUDE.md
---

# Error: macOS `/var` → `/private/var` symlink breaks path assertions

## Signature

macOS `/var` → `/private/var` symlink breaks path assertions

## Root Cause

`_validate_file_path()` calls `Path.resolve()`, which follows the macOS symlink from `/var/folders/...` to `/private/var/folders/...`. Tests using `tempfile.NamedTemporaryFile` get unresolved paths from `f.name` but resolved paths from validated code.

## Resolution

1. assert against `str(Path(f.name).resolve())` instead of `f.name`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
