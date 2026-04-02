---
type: warning
name: session-hooks-may-be-vestigial
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Warning: Session hooks may be vestigial

## Condition

`session_end.py` saves near-empty shells (zero tokens, no patterns detected)

## Risk

Ignoring this guidance may cause: Session hooks may be vestigial

## Mitigation

1. `session_end.py` saves near-empty shells (zero tokens, no patterns detected)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Session hooks may be vestigial
