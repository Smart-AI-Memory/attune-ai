---
name: hooks
source: content/features/hooks.md
tags:
- hooks
- webhooks
- events
- automation
type: tip
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
