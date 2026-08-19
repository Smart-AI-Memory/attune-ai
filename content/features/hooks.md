---
feature: hooks
summary: The hook system — register handlers for lifecycle events, fire them in-process, or drive them from config
tags: [hooks, webhooks, events, automation]
source_globs:
  - src/attune/hooks/**
nav:
  help: hooks
  mkdocs:
    how-to: how-to/hooks
    architecture: architecture/hooks
    reference: reference/hooks
---

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

## Quickstart

Register an in-process handler and fire it:

```python
from attune.hooks import HookRegistry, HookEvent

registry = HookRegistry()


def on_pre_tool(**context) -> dict:        # context arrives as kwargs
    return {"blocked": False, "tool": context.get("tool_name")}


registry.register(HookEvent.PRE_TOOL_USE, on_pre_tool)
results = registry.fire_sync(HookEvent.PRE_TOOL_USE, {"tool_name": "Bash"})
print(results)
```

## Tasks

### Register and fire an in-process hook

```python
from attune.hooks import HookRegistry, HookEvent

registry = HookRegistry()


def guard(**context) -> dict:
    return {"blocked": context.get("tool_name") == "Bash"}


hook_id = registry.register(HookEvent.PRE_TOOL_USE, guard, priority=10)
results = registry.fire_sync(HookEvent.PRE_TOOL_USE, {"tool_name": "Bash"})
print(hook_id, results[0]["success"], results[0]["output"])
```

**Verify:** `register(...)` returns a hook id (a `str`). `fire_sync`
runs every matching handler — calling each as `handler(**context)` — and
returns a list of result dicts (a success record carries `event`,
`hook`, `description`, `success`, `output`, `error`, `duration_ms`; an
error record is a subset). `fire(...)` is the async variant.

### Load hooks from YAML config

**Goal:** declare hooks in a file instead of code.

**Steps:** `HookConfig.from_yaml(path)` returns a `HookConfig`;
`get_hooks_for_event(event)` lists the `HookRule`s for an event. Each
rule's `hooks` are `HookDefinition`s an executor can run.

```python
from attune.hooks import HookConfig, HookEvent

config = HookConfig.from_yaml("hooks.yaml")
for rule in config.get_hooks_for_event(HookEvent.PRE_TOOL_USE):
    print(rule.description, rule.priority)
```

**Verify:** `from_yaml` is a constructor returning `HookConfig`;
`get_hooks_for_event` returns `list[HookRule]`.

### Execute a configured hook

```python
import asyncio

from attune.hooks import HookExecutor, HookDefinition
from attune.hooks.config import HookType

hook = HookDefinition(type=HookType.COMMAND, command="echo hi", timeout=5)
executor = HookExecutor()
result = asyncio.run(executor.execute(hook, {"tool_name": "Bash"}))
print(result)
```

**Verify:** `HookExecutor.execute(hook, context)` is **async** — await
it; it returns a result dict.

## Reference

| Symbol | Kind | Purpose |
|--------|------|---------|
| `HookEvent` | enum | `PRE_TOOL_USE`/`POST_TOOL_USE`/`SESSION_START`/`SESSION_END`/`PRE_COMPACT`/`PRE_COMMAND`/`POST_COMMAND`/`STOP`; values are Claude Code event names. |
| `HookRegistry(config=None)` | class | `register(event, handler, description="", matcher=None, priority=0) -> str`, `fire` (async) / `fire_sync`, `get_matching_hooks`, `unregister`, `get_execution_log`, `get_stats`, `load_config`. |
| `HookExecutor(python_handlers=None)` | class | `execute(hook, context)` — **async**. |
| `HookDefinition(type=HookType.PYTHON, command, description="", timeout=30, async_execution=False, on_error="log")` | pydantic model | A configured hook. |
| `HookConfig(hooks={}, enabled=True, log_executions=True, default_timeout=30)` | pydantic model | `from_yaml(path)`, `add_hook(event, hook, matcher=None, priority=0)`, `get_hooks_for_event(event)`, `to_yaml`. |
| `HookType` (`attune.hooks.config`) | enum | `COMMAND` / `PYTHON` / `WEBHOOK`. |
| `HookRule` (`attune.hooks.config`) | pydantic model | `matcher`, `hooks`, `enabled`, `priority`, `description`. |

## Comparison

| | `HookRegistry` | `HookConfig` + `HookExecutor` | bundled scripts |
|--|----------------|------------------------------|-----------------|
| Style | imperative, in-process Python handlers | declarative YAML rules | shipped Claude Code hooks |
| Define | `register(event, fn)` | `HookDefinition` / `from_yaml` | files in `attune/hooks/scripts/` |
| Run | `fire` / `fire_sync` | `HookExecutor.execute` | invoked by Claude Code |

The registry is for embedding hooks in Python; the config + executor are
for declarative hooks; the scripts are the concrete hooks the plugin
registers with Claude Code.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `handler() got an unexpected keyword argument` | handler written as `def handler(context)` | context is unpacked as kwargs — use `def handler(**context)` | high |
| `RuntimeWarning: coroutine 'fire' was never awaited` | `fire`/`execute` called without `await` | use `fire_sync`, or `await` the async ones | high |
| Hook never fires | wrong `HookEvent`, or a `matcher` excludes the context | check the event; inspect `get_matching_hooks(event, context)` | medium |
| `ValidationError` building a `HookDefinition` | `timeout` outside 1–300, or missing `command` | supply a valid `command` and `timeout` | medium |

### Risk areas

- **Handlers take kwargs.** `def handler(**context)`, not
  `def handler(context)`.
- **`fire` and `execute` are async; `fire_sync` is sync.**
- **Priority + matcher decide what runs.** A `matcher` can exclude a
  handler even for the right event.

### Diagnosis order

1. Did it fire? `registry.get_matching_hooks(event, context)`.
2. Handler signature — `**context`?
3. Async-not-awaited? Use `fire_sync` or `await`.
4. For config hooks, `HookConfig.get_hooks_for_event(event)`.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** Author-curated seeds, merged
> by the FAQ Generator with live signals. Not projected verbatim.

- **Q:** What events can I hook?
  **A:** The `HookEvent` enum — `PRE_TOOL_USE`, `POST_TOOL_USE`,
  `SESSION_START`/`SESSION_END`, `PRE_COMPACT`,
  `PRE_COMMAND`/`POST_COMMAND`, `STOP`. Their values are the Claude Code
  event names.
- **Q:** How should a handler be written?
  **A:** It receives the context unpacked as kwargs — `def
  handler(**context): ...`. Register it with
  `HookRegistry.register(event, handler)`.
- **Q:** Sync or async?
  **A:** `fire_sync` is synchronous; `fire` and `HookExecutor.execute`
  are async.
- **Q:** Where are the hooks the plugin actually runs?
  **A:** Under `attune/hooks/scripts/` (e.g. `security_guard`,
  `worktree_path_guard`, `lessons_reminder`).

## Notes & tips

- **`def handler(**context)`.** The single most common mistake is a
  positional `context` parameter.
- **`fire_sync` for synchronous code.** `fire` / `execute` are async.
- **`HookEvent` values are the Claude Code names.** One enum spans the
  in-process and Claude Code contracts.
- **Declarative vs imperative.** `HookConfig`/`from_yaml` for config;
  `HookRegistry` for embedded Python.

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
