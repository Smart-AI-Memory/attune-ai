---
type: tip
name: hooks-tip
feature: hooks
depth: tip
generated_at: 2026-08-20T12:28:08.536306+00:00
source_hash: 6a74897099089de928581379ad010c61f7449b270204090c659e122d08d62c1c
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
