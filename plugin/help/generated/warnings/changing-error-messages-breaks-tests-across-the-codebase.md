---
type: warning
name: changing-error-messages-breaks-tests-across-the-codebase
confidence: Verified
tags: [testing, security, git]
source: .claude/CLAUDE.md
---

# Warning: Changing error messages breaks tests across the codebase

## Condition

Updating `_validate_file_path()`'s error from `"path must be within"` to `"outside allowed directory"` broke 10 test files

## Risk

Updating `_validate_file_path()`'s error from `"path must be within"` to `"outside allowed directory"` broke 10 test files

## Mitigation

1. Before changing any error message in a shared function, grep the entire test suite for `match="<old message>"` and update all callers in the same commit

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Changing error messages breaks tests across the codebase
