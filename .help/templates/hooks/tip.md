---
type: tip
name: hooks-tip
feature: hooks
depth: tip
generated_at: 2026-06-24T01:45:59.743282+00:00
source_hash: 4b00173384f5e97dd450a6b8b69e5253088cb776441337b23c6bf960f70c76f7
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
