---
type: comparison
name: hooks-comparison
feature: hooks
depth: comparison
generated_at: 2026-06-24T01:45:59.743282+00:00
source_hash: 4b00173384f5e97dd450a6b8b69e5253088cb776441337b23c6bf960f70c76f7
status: generated
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
