# Hooks

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

## Design & extension

### Design decisions

- **One enum, two worlds.** `HookEvent` labels both in-process
  registration and the Claude Code hook contract (its values are the
  Claude Code event names).
- **Registry vs config.** Imperative `HookRegistry` and declarative
  `HookConfig`/`HookExecutor` are separate surfaces over the same
  events.
- **Bounded, typed definitions.** `HookDefinition` is a pydantic model
  with a `timeout` bounded to 1–300 s and an `on_error` policy.

### Extension points

- **Add an in-process hook:** `HookRegistry.register(event, handler,
  priority=...)`.
- **Add a declarative hook:** a `HookDefinition` in `HookConfig`
  (`add_hook` or YAML), run by `HookExecutor`.
- **Ship a script:** add a module under `attune/hooks/scripts/` and
  register it in the plugin's hook config.

<!-- attune-generated: source_hash=135910a198c946084ebe186e1f9f9879826026c95886aa2c85c739e52893fee8 feature=hooks kind=architecture generated_at=2026-08-19 -->
