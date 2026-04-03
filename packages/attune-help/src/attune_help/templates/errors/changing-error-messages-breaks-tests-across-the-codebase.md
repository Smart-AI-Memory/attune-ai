---
type: error
name: changing-error-messages-breaks-tests-across-the-codebase
confidence: Verified
tags: [testing, security, git]
source: .claude/CLAUDE.md
---

# Error: Changing error messages breaks tests across the codebase

## Signature

` broke 10 test files. Before changing any error message in a shared function, grep the entire test suite for `match=

## Root Cause

Updating `_validate_file_path()`'s error from `"path must be within"` to `"outside allowed directory"` broke 10 test files. Before changing any error message in a shared function, grep the entire test suite for `match="<old message>"` and update all callers in the same commit.

## Resolution

1. Updating `_validate_file_path()`'s error from `"path must be within"` to `"outside allowed directory"` broke 10 test files

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
