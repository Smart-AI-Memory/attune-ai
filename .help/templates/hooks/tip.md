---
type: tip
name: hooks-tip
feature: hooks
depth: tip
generated_at: 2026-08-20T13:06:14.232086+00:00
source_hash: 5aba5457cc740ed70cb22f0f6e950c97d47eeeac8faabd7f0a716459b548cb13
status: generated
---

# The hook system — shipped scripts that Claude Code runs on session and tool lifecycle events

## Notes & tips

- **Fail open on bad input.** Exit `0` on any non-JSON / non-dict
  stdin; only a deliberate policy decision should exit `2`.
- **Only `2` blocks.** Every other exit code allows the tool.
- **Keep hooks fast.** They run on the critical path under a timeout.
- **One event name space.** The event names (`PreToolUse`, …) are the
  Claude Code names.
