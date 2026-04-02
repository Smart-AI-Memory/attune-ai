---
type: error
name: codeql-py-clear-text-logging-sensitive-data-traces-data-flow
confidence: Verified
tags: [security]
source: .claude/CLAUDE.md
---

# Error: CodeQL `py/clear-text-logging-sensitive-data` traces data flow,
  not literal secrets

## Signature

CodeQL `py/clear-text-logging-sensitive-data` traces data flow,
  not literal secrets

## Root Cause

CodeQL flagged `user_id` in a log message inside `security.py` even though only the count of secrets was logged (not secret values). It traces any variable that flows through a security-sensitive method.

## Resolution

1. use `%s` formatting without user identifiers, or move audit correlation to the dedicated audit logger which is designed for that purpose

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: CodeQL `py/clear-text-logging-sensitive-data` traces data flow,
  not literal secrets
