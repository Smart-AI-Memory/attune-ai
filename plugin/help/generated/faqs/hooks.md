---
name: hooks
source: content/features/hooks.md
tags:
- hooks
- webhooks
- events
- automation
type: faq
---

# Hooks FAQ

## What events can I hook?

The `HookEvent` enum — `PRE_TOOL_USE`, `POST_TOOL_USE`,
`SESSION_START`/`SESSION_END`, `PRE_COMPACT`/`POST_COMPACT`,
`PRE_COMMAND`/`POST_COMMAND`, `STOP`. Their values are the Claude Code
event names.

## How should a handler be written?

It receives the context unpacked as kwargs — `def
handler(**context): ...`. Register it with
`HookRegistry.register(event, handler)`.

## Sync or async?

`fire_sync` is synchronous; `fire` and `HookExecutor.execute`
are async.

## Where are the hooks the plugin actually runs?

Under `attune/hooks/scripts/` (e.g. `security_guard`,
`worktree_path_guard`, `lessons_reminder`).
