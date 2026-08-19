---
type: faq
name: hooks-faq
feature: hooks
depth: faq
generated_at: 2026-08-19T15:41:55.951394+00:00
source_hash: 135910a198c946084ebe186e1f9f9879826026c95886aa2c85c739e52893fee8
status: generated
---

# Hooks FAQ

## What events can I hook?

The `HookEvent` enum — `PRE_TOOL_USE`, `POST_TOOL_USE`,
`SESSION_START`/`SESSION_END`, `PRE_COMPACT`,
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
