---
type: comparison
name: hooks-comparison
feature: hooks
depth: comparison
generated_at: 2026-08-19T15:41:55.951394+00:00
source_hash: 135910a198c946084ebe186e1f9f9879826026c95886aa2c85c739e52893fee8
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
