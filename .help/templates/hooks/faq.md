---
type: faq
name: hooks-faq
feature: hooks
depth: faq
generated_at: 2026-07-14T15:58:53.225546+00:00
source_hash: 4b00173384f5e97dd450a6b8b69e5253088cb776441337b23c6bf960f70c76f7
status: generated
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
