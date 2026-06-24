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

# The hook system — register handlers for lifecycle events, fire them in-process, or drive them from config

## Comparison

| | `HookRegistry` | `HookConfig` + `HookExecutor` | bundled scripts |
|--|----------------|------------------------------|-----------------|
| Style | imperative, in-process Python handlers | declarative YAML rules | shipped Claude Code hooks |
| Define | `register(event, fn)` | `HookDefinition` / `from_yaml` | files in `attune/hooks/scripts/` |
| Run | `fire` / `fire_sync` | `HookExecutor.execute` | invoked by Claude Code |

The registry is for embedding hooks in Python; the config + executor are
for declarative hooks; the scripts are the concrete hooks the plugin
registers with Claude Code.
