---
name: hooks
source: content/features/hooks.md
tags:
- hooks
- webhooks
- events
- automation
type: note
---

# The hook system — register handlers for lifecycle events, fire them in-process, or drive them from config

## Overview

`attune.hooks` is an **event system**: it lets code (and config) react
to lifecycle events — before/after a tool runs, at session start/end,
before compaction, and on stop. The public surface, exported from
`attune.hooks`, is five symbols:

- **`HookEvent`** — the events you can hook (`PRE_TOOL_USE`,
  `POST_TOOL_USE`, `SESSION_START`, `SESSION_END`, `PRE_COMPACT`,
  `PRE_COMMAND`, `POST_COMMAND`, `STOP`).
- **`HookRegistry`** — register Python handlers for events and fire
  them in-process.
- **`HookExecutor`** — run a configured `HookDefinition` (command,
  Python, or webhook).
- **`HookConfig`** / **`HookDefinition`** — the declarative,
  config-driven hooks (loaded from YAML).

The plugin also ships concrete hook scripts under
`attune/hooks/scripts/` (e.g. `security_guard`, `worktree_path_guard`,
`lessons_reminder`) — these are the hooks Claude Code actually runs.

## Concepts

### `HookEvent`

The lifecycle events. Their **values are the Claude Code event names** —
e.g. `HookEvent.PRE_TOOL_USE.value == "PreToolUse"` — so the same enum
labels in-process registration and the Claude Code hook contract.

### `HookRegistry` — in-process handlers

`HookRegistry(config=None)` is the programmatic surface.
`register(event, handler, description="", matcher=None, priority=0)`
adds a handler and returns a hook id. **Handlers receive the context
dict unpacked as keyword arguments** — write `def handler(**context)`,
not `def handler(context)`. Fire with `fire(event, context=None)`
(async) or `fire_sync(event, context=None)` (sync); both return a list
of per-hook result dicts — a success record carries `event`, `hook`,
`description`, `success`, `output`, `error`, `duration_ms`; an error
record is a subset (`event`, `hook`, `success`, `error`). `get_matching_hooks`, `unregister`,
`get_execution_log`, `get_stats`, and `load_config` round it out.

### `HookExecutor` and `HookDefinition`

`HookDefinition` (a pydantic model) describes a configured hook: `type`
(`HookType.COMMAND` / `PYTHON` / `WEBHOOK`, default `PYTHON`),
`command`, `description`, `timeout` (1–300 s, default 30),
`async_execution` (default `False`), `on_error` (default `"log"`).
`HookExecutor(python_handlers=None).execute(hook, context)` (async) runs
one.

### `HookConfig` — declarative, config-driven hooks

`HookConfig` (pydantic) holds the declarative rules: `hooks` (a dict of
event → list of `HookRule`), plus `enabled`, `log_executions`, and
`default_timeout`. Load it with `HookConfig.from_yaml(yaml_path)`, build
it with `add_hook(event, hook, matcher=None, priority=0)`, and query it
with `get_hooks_for_event(event)`. A `HookRule` carries a `matcher`, its
`hooks`, `enabled`, `priority`, and `description`.

## Notes & tips

- **`def handler(**context)`.** The single most common mistake is a
  positional `context` parameter.
- **`fire_sync` for synchronous code.** `fire` / `execute` are async.
- **`HookEvent` values are the Claude Code names.** One enum spans the
  in-process and Claude Code contracts.
- **Declarative vs imperative.** `HookConfig`/`from_yaml` for config;
  `HookRegistry` for embedded Python.
