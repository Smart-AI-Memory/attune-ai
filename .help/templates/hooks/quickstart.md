---
type: quickstart
name: hooks-quickstart
feature: hooks
depth: quickstart
generated_at: 2026-08-19T15:41:55.951394+00:00
source_hash: 135910a198c946084ebe186e1f9f9879826026c95886aa2c85c739e52893fee8
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
