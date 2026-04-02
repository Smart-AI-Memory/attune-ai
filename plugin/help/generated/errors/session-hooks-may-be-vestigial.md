---
type: error
name: session-hooks-may-be-vestigial
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: Session hooks may be vestigial

## Signature

Session hooks may be vestigial

## Root Cause

`session_end.py` saves near-empty shells (zero tokens, no patterns detected). Verify they are wired to collect meaningful data before building on top of them or advertising session memory as a feature.

## Resolution

1. `session_end.py` saves near-empty shells (zero tokens, no patterns detected)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
