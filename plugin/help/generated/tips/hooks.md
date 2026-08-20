---
name: hooks
source: content/features/hooks.md
tags:
- hooks
- webhooks
- events
- automation
type: tip
---

# The hook system — shipped scripts that Claude Code runs on session and tool lifecycle events

## Notes & tips

- **Fail open on bad input.** Exit `0` on any non-JSON / non-dict
  stdin; only a deliberate policy decision should exit `2`.
- **Only `2` blocks.** Every other exit code allows the tool.
- **Keep hooks fast.** They run on the critical path under a timeout.
- **One event name space.** The event names (`PreToolUse`, …) are the
  Claude Code names.
