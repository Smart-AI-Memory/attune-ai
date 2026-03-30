---
type: faq
name: lazy-imports-inside-function-bodies-cant-be-patched-with
tags: [testing, imports, claude-code]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Lazy imports inside function bodies can't be patched with
  `patch("module.Name")`?

## Answer

`HookEvent`, `HookRegistry`, and similar names imported inside function bodies are never bound at module scope. `patch("attune.commands.context.HookEvent")` raises `AttributeError`.


**Fix:**

- Use `patch.dict("sys.modules", ...)` to simulate `ImportError`, or use the real value for happy-path tests

```
HookRegistry
```

## Related Topics
- **Error**: Detailed error: Lazy imports inside function bodies can't be patched with
  `patch("module.Name")`
