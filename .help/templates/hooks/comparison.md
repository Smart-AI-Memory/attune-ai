---
type: comparison
name: hooks-comparison
feature: hooks
depth: comparison
generated_at: 2026-08-20T12:28:08.536306+00:00
source_hash: 6a74897099089de928581379ad010c61f7449b270204090c659e122d08d62c1c
status: generated
---

# The hook system — shipped scripts that Claude Code runs on session and tool lifecycle events

## Comparison

| | attune bundled scripts | ad-hoc project hook |
|--|------------------------|---------------------|
| Define | module in `attune/hooks/scripts/` | any executable |
| Wire | plugin `hooks.json` | your `settings.json` hooks |
| Run | invoked by Claude Code | invoked by Claude Code |

Both are Claude Code hooks over the same stdin/exit-code contract;
attune's ship with the plugin and are maintained in-tree.
