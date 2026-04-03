---
type: warning
name: stop-hooks-loop-without-a-sentinel
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Warning: Stop hooks loop without a sentinel

## Condition

Exit code 2 blocks one stop attempt but the next attempt triggers the hook again, creating an infinite loop

## Risk

Exit code 2 blocks one stop attempt but the next attempt triggers the hook again, creating an infinite loop

## Mitigation

1. Use a TTL sentinel file (`~/.attune/lessons_reminded`) to fire the reminder only once per session

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Stop hooks loop without a sentinel
