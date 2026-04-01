---
type: error
name: datetime-utcnow-datetime-nowtimezone-utc-cascades-through-the
confidence: Verified
tags: [testing, python]
source: .claude/CLAUDE.md
---

# Error: `datetime.utcnow()` → `datetime.now(timezone.utc)` cascades
  through the entire codebase

## Signature

TypeError: can't compare offset-naive and offset-aware datetimes

## Root Cause

Replacing `utcnow()` (naive) with `now(timezone.utc)` (aware) in source code causes `TypeError: can't compare offset-naive and offset-aware datetimes` everywhere that stored/parsed timestamps interact with the new aware values. This includes `_parse_timestamp()` helpers, `fromisoformat()` calls that strip `Z`, and test fixtures that create naive datetimes. Plan for a full sweep of both src/ and tests/ — not just the files you initially changed.

## Resolution

1. Replacing `utcnow()` (naive) with `now(timezone.utc)` (aware) in source code causes `TypeError: can't compare offset-naive and offset-aware datetimes` everywhere that stored/parsed timestamps interact with the new aware values

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `datetime.utcnow()` → `datetime.now(timezone.utc)` cascades
  through the entire codebase
- Task: Update test mocks and assertions
