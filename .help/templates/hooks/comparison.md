---
type: comparison
name: hooks-comparison
feature: hooks
depth: comparison
generated_at: 2026-08-20T13:06:14.232086+00:00
source_hash: 5aba5457cc740ed70cb22f0f6e950c97d47eeeac8faabd7f0a716459b548cb13
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
