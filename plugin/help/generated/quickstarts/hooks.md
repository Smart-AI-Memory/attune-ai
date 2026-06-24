---
name: hooks
source: content/features/hooks.md
tags:
- hooks
- webhooks
- events
- automation
type: quickstart
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
