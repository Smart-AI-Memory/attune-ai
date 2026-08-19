# Hooks

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

<!-- attune-generated: source_hash=135910a198c946084ebe186e1f9f9879826026c95886aa2c85c739e52893fee8 feature=hooks kind=reference generated_at=2026-08-19 -->
