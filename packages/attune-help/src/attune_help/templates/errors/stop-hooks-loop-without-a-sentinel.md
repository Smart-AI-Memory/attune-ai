---
type: error
name: stop-hooks-loop-without-a-sentinel
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: Stop hooks loop without a sentinel

## Signature

Stop hooks loop without a sentinel

## Root Cause

Exit code 2 blocks one stop attempt but the next attempt triggers the hook again, creating an infinite loop. Use a TTL sentinel file (`~/.attune/lessons_reminded`) to fire the reminder only once per session.

## Resolution

1. Use a TTL sentinel file (`~/.attune/lessons_reminded`) to fire the reminder only once per session

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Stop hooks loop without a sentinel
