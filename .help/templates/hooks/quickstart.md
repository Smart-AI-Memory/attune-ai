---
type: quickstart
name: hooks-quickstart
feature: hooks
depth: quickstart
generated_at: 2026-06-24T01:45:59.743282+00:00
source_hash: 4b00173384f5e97dd450a6b8b69e5253088cb776441337b23c6bf960f70c76f7
status: generated
---

# The hook system — register handlers for lifecycle events, fire them in-process, or drive them from config

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
