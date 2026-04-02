---
type: warning
name: background-processes-from-previous-sessions-persist-across
confidence: Verified
source: .claude/CLAUDE.md
---

# Warning: Background processes from previous sessions persist across
  restarts

## Condition

Long-running processes started by Claude (e.g

## Risk

`npm run dev`) survive session end and keep running silently

## Mitigation

1. Always `kill` them explicitly when removing a feature, and check `ps aux` if unexpected behavior is observed (Chrome tabs opening, ports already in use, etc.)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Background processes from previous sessions persist across
  restarts
