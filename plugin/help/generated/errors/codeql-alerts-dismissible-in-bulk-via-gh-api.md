---
type: error
name: codeql-alerts-dismissible-in-bulk-via-gh-api
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Error: CodeQL alerts dismissible in bulk via `gh api`

## Signature

CodeQL alerts dismissible in bulk via `gh api`

## Root Cause

Use `gh api repos/OWNER/REPO/code-scanning/alerts/ID -X PATCH -f state=dismissed -f dismissed_reason="false positive" -f dismissed_comment="..."` to batch-dismiss with documented reasons. Valid reasons: `false positive`, `won't fix`, `used in tests`.

## Resolution

1. Use `gh api repos/OWNER/REPO/code-scanning/alerts/ID -X PATCH -f state=dismissed -f dismissed_reason="false positive" -f dismissed_comment="..."` to batch-dismiss with documented reasons

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: CodeQL alerts dismissible in bulk via `gh api`
- Task: Update test mocks and assertions
