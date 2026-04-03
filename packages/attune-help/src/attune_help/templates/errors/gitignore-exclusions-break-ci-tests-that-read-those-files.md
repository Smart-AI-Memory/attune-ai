---
type: error
name: gitignore-exclusions-break-ci-tests-that-read-those-files
confidence: Verified
tags: [ci, testing]
source: .claude/CLAUDE.md
---

# Error: `.gitignore` exclusions break CI tests that read those
  files

## Signature

`.gitignore` exclusions break CI tests that read those
  files

## Root Cause

If tests call `read_spec(".claude/plans/foo.md")` but `.gitignore` excludes `.claude/plans/`, CI will never have the file. Either track the files or skip the tests when absent.

## Resolution

1. If tests call `read_spec(".claude/plans/foo.md")` but `.gitignore` excludes `.claude/plans/`, CI will never have the file

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: `.gitignore` exclusions break CI tests that read those
  files
- Task: Update test mocks and assertions
