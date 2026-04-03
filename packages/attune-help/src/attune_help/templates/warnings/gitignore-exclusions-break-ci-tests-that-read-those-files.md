---
type: warning
name: gitignore-exclusions-break-ci-tests-that-read-those-files
confidence: Verified
tags: [ci, testing]
source: .claude/CLAUDE.md
---

# Warning: `.gitignore` exclusions break CI tests that read those
  files

## Condition

If tests call `read_spec(".claude/plans/foo.md")` but `.gitignore` excludes `.claude/plans/`, CI will never have the file

## Risk

Ignoring this guidance may cause: `.gitignore` exclusions break CI tests that read those
  files

## Mitigation

1. If tests call `read_spec(".claude/plans/foo.md")` but `.gitignore` excludes `.claude/plans/`, CI will never have the file

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `.gitignore` exclusions break CI tests that read those
  files
