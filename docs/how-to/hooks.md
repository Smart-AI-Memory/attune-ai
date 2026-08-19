# Hooks

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

<!-- attune-generated: source_hash=135910a198c946084ebe186e1f9f9879826026c95886aa2c85c739e52893fee8 feature=hooks kind=how-to generated_at=2026-08-19 -->
