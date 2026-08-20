---
name: hooks
source: content/features/hooks.md
tags:
- hooks
- webhooks
- events
- automation
type: comparison
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
