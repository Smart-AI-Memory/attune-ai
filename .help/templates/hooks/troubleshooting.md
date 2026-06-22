---
type: troubleshooting
name: hooks-troubleshooting
feature: hooks
depth: troubleshooting
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 92f76c4d4d77b21e59b9a6aed8e65dd221371f5ce10f2941171a5c0310c232c1
status: generated
---

# Troubleshoot hooks

## Before you start

The hook system fires callbacks at Claude Code lifecycle events. It is built around three collaborating classes: `HookRegistry` (registers and dispatches hooks), `HookExecutor` / `HookExecutorSync` (runs a single `HookDefinition`), and `HookConfig` (loads rules from YAML and supplies them to the registry). Most problems fall into one of three categories: a hook never fires, a hook fires but produces unexpected output, or a hook fires but raises an error.

## Symptom table

| If you observe | Check |
|---|---|
| Hook never fires | Call `registry.get_matching_hooks(event, context)` — if the list is empty, the `HookMatcher` condition is not satisfied or the hook was never registered for that `HookEvent`. |
| Hook fires for the wrong events | Inspect `registry.get_stats()` — compare the event counts against what you expect, then review the `HookMatcher.matches()` logic for the affected rule. |
| Hook fires but returns unexpected output | Call `registry.get_execution_log(event_filter=<your_event>)` and examine the result dicts returned by `HookExecutor.execute()`. |
| Hook registered via YAML never loads | Confirm `HookConfig.from_yaml(yaml_path)` succeeds and that you subsequently called `registry.load_config(config)`. |
| Python handler is never called | Verify the handler name is a key in the `python_handlers` dict passed to `HookExecutor(python_handlers={...})`. |
| Intermittent failures | Check for mutable state outside the handler callable (globals, module-level caches). Confirm that `context` dicts are not mutated between `fire()` calls. |
| `fire()` hangs or is very slow | Switch to `fire_sync()` via `HookRegistry.fire_sync()` to isolate async overhead. Then check the handler for blocking I/O or unbounded loops. |
| Security-guard hook blocks a command unexpectedly | Call `validate_bash_command(command)` or `validate_file_path(file_path)` directly and inspect the returned `(bool, str)` tuple to see the rejection reason. |

## Diagnosis steps

Work through these in order — each step costs more time than the one before it.

### 1. Confirm the hook is registered

```python
hooks = registry.get_matching_hooks(event, context)
print(hooks)  # empty list means nothing is registered for this event + context
```

If the list is empty, either `registry.register(event, handler, ...)` was never called, or the `HookMatcher` returned `False` for the provided `context`. Add a temporary matcher that always returns `True` to distinguish the two cases:

```python
class AlwaysMatch:
    def matches(self, context):
        return True
```

### 2. Check the execution log

```python
log = registry.get_execution_log(limit=20, event_filter=your_event)
for entry in log:
    print(entry)
```

`get_execution_log()` returns the most recent executions. An empty log after `fire()` confirms the hook did not execute at all. Non-empty entries show the result dict from each `HookExecutor.execute()` call, which includes any errors the handler raised.

### 3. Review registry stats

```python
stats = registry.get_stats()
print(stats)
```

`get_stats()` shows aggregate counts per event. A count of zero for an event you expected to fire points to a registration or dispatch problem rather than an executor problem.

### 4. Fire the hook in isolation

Strip the call down to its required arguments and fire directly:

```python
from hooks import HookRegistry, HookConfig, HookEvent

registry = HookRegistry()
registry.register(HookEvent.YOUR_EVENT, your_handler, description="debug test")
results = registry.fire_sync(HookEvent.YOUR_EVENT, context={"key": "value"})
print(results)
```

Using `fire_sync()` removes async scheduling from the equation and gives you a synchronous result or a traceback immediately.

### 5. Test the executor in isolation

If `fire_sync()` produces the wrong result, test the executor directly:

```python
from hooks.executor import HookExecutorSync

executor = HookExecutorSync(python_handlers={"my_handler": your_callable})
result = executor.execute(hook_definition, context)
print(result)
```

This confirms whether the problem is in dispatch (`HookRegistry`) or execution (`HookExecutor`).

### 6. Run the related tests

```bash
pytest -k "hooks" -v
```

A failing test that covers your path gives you a reproducible baseline and a fixture you can adapt.

## Common fixes

**Hook never fires — missing `load_config` call**

If you loaded rules from YAML, you must pass the config to the registry explicitly:

```python
config = HookConfig.from_yaml("hooks.yaml")
registry = HookRegistry()
registry.load_config(config)   # required — the registry does not auto-load
```

**Hook never fires — matcher rejects the context**

`HookMatcher.matches(context)` receives the dict you pass to `fire()`. If a required key is absent or has the wrong value, the hook is silently skipped. Add logging inside `matches()` or temporarily replace the matcher with one that always returns `True` to verify.

**Python handler not called — key missing from `python_handlers`**

`HookExecutor` looks up handlers by name in the dict you supply at construction time. If the key is absent, the handler is not called. Confirm the key matches exactly:

```python
executor = HookExecutorSync(python_handlers={"expected_key": your_callable})
```

**Handler ID lost — cannot unregister**

`registry.register(...)` returns a `str` handler ID. If you discard it, you cannot call `registry.unregister(handler_id)` later. Store the ID when you register:

```python
handler_id = registry.register(HookEvent.YOUR_EVENT, your_handler)
# later:
registry.unregister(handler_id)
```

**Stale execution log skewing diagnosis**

The log accumulates across calls. Clear it before a focused test run:

```python
registry.clear_execution_log()
# then reproduce the failure
```

**Dependency or environment drift**

If hooks worked previously without a code change, confirm your environment is consistent:

```bash
pip show <dependency-name>
```

This is a change outside the hooks feature itself — a dependency upgrade can alter behavior in `HookExecutor` or in your handler callables.

## Source files

- `src/attune/hooks/**`

**Tags:** `hooks`, `events`, `automation`, `HookRegistry`, `HookExecutor`, `HookConfig`

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 72 (code fence) | error | `from hooks import …` — module not importable |
| Line 87 (code fence) | error | `from hooks.executor import …` — module not importable |
