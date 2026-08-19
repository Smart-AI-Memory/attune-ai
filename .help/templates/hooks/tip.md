---
type: tip
name: hooks-tip
feature: hooks
depth: tip
generated_at: 2026-08-19T15:41:55.951394+00:00
source_hash: 135910a198c946084ebe186e1f9f9879826026c95886aa2c85c739e52893fee8
status: generated
---

# The hook system — register handlers for lifecycle events, fire them in-process, or drive them from config

## Notes & tips

- **`def handler(**context)`.** The single most common mistake is a
  positional `context` parameter.
- **`fire_sync` for synchronous code.** `fire` / `execute` are async.
- **`HookEvent` values are the Claude Code names.** One enum spans the
  in-process and Claude Code contracts.
- **Declarative vs imperative.** `HookConfig`/`from_yaml` for config;
  `HookRegistry` for embedded Python.
