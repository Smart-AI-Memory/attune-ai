---
type: warning
name: hooks-warning
feature: hooks
depth: warning
generated_at: 2026-06-24T01:45:59.743282+00:00
source_hash: 4b00173384f5e97dd450a6b8b69e5253088cb776441337b23c6bf960f70c76f7
status: generated
---

# The hook system — register handlers for lifecycle events, fire them in-process, or drive them from config

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
