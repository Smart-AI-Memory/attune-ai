---
type: warning
name: codeql-alerts-dismissible-in-bulk-via-gh-api
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Warning: CodeQL alerts dismissible in bulk via `gh api`

## Condition

Use `gh api repos/OWNER/REPO/code-scanning/alerts/ID -X PATCH -f state=dismissed -f dismissed_reason="false positive" -f dismissed_comment="..."` to batch-dismiss with documented reasons

## Risk

Ignoring this guidance may cause: CodeQL alerts dismissible in bulk via `gh api`

## Mitigation

1. Use `gh api repos/OWNER/REPO/code-scanning/alerts/ID -X PATCH -f state=dismissed -f dismissed_reason="false positive" -f dismissed_comment="..."` to batch-dismiss with documented reasons

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: CodeQL alerts dismissible in bulk via `gh api`
