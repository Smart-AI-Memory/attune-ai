---
type: error
name: background-processes-from-previous-sessions-persist-across
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: Background processes from previous sessions persist across
  restarts

## Signature

Background processes from previous sessions persist across
  restarts

## Root Cause

Long-running processes started by Claude (e.g. `npm run dev`) survive session end and keep running silently. They can open browser tabs, consume ports, or interfere with the next session. Always `kill` them explicitly when removing a feature, and check `ps aux` if unexpected behavior is observed (Chrome tabs opening, ports already in use, etc.).

## Resolution

1. Always `kill` them explicitly when removing a feature, and check `ps aux` if unexpected behavior is observed (Chrome tabs opening, ports already in use, etc.)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Background processes from previous sessions persist across
  restarts
