---
type: warning
name: dont-append-z-to-timezone-aware-isoformat
confidence: Verified
tags: [python]
source: .claude/CLAUDE.md
---

# Warning: Don't append `+ "Z"` to timezone-aware `.isoformat()`

## Condition

`datetime.now(timezone.utc).isoformat()` already produces `2026-03-08T12:00:00+00:00`

## Risk

Ignoring this guidance may cause: Don't append `+ "Z"` to timezone-aware `.isoformat()`

## Mitigation

1. `datetime.now(timezone.utc).isoformat()` already produces `2026-03-08T12:00:00+00:00`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Don't append `+ "Z"` to timezone-aware `.isoformat()`
