---
type: error
name: dont-append-z-to-timezone-aware-isoformat
confidence: Verified
tags: [python]
source: .claude/CLAUDE.md
---

# Error: Don't append `+ "Z"` to timezone-aware `.isoformat()`

## Signature

Don't append `+ "Z"` to timezone-aware `.isoformat()`

## Root Cause

`datetime.now(timezone.utc).isoformat()` already produces `2026-03-08T12:00:00+00:00`. Appending `+ "Z"` creates `+00:00Z` which, when passed through `.replace("Z", "+00:00")`, becomes the invalid `+00:00+00:00`. After migrating to timezone-aware datetimes, grep for `.isoformat() + "Z"` and remove the suffix.

## Resolution

1. `datetime.now(timezone.utc).isoformat()` already produces `2026-03-08T12:00:00+00:00`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
