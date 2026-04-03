---
type: error
name: windows-path-resolve-prepends-the-drive-letter-to-unix-paths
confidence: Verified
tags: [testing, security, windows, python]
source: .claude/CLAUDE.md
---

# Error: Windows `Path.resolve()` prepends the drive letter to Unix
  paths

## Signature

Windows `Path.resolve()` prepends the drive letter to Unix
  paths

## Root Cause

`Path("/code").resolve()` on Windows returns `D:\code`, not `/code`. Tests that assert exact path strings passed through `_validate_file_path` fail on Windows CI.

## Resolution

1. patch `_validate_file_path` in tests that verify handler logic (not path validation) so paths pass through unchanged

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
