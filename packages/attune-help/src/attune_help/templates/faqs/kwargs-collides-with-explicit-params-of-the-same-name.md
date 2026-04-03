---
type: faq
name: kwargs-collides-with-explicit-params-of-the-same-name
tags: [python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about **kwargs collides with explicit params of the same name?

## Answer

If a helper like `_result_from_plan(plan, status, **kwargs)` builds a dataclass and callers pass `reason_codes=...` in `**kwargs`, it silently conflicts with any `reason_codes=...` already set inside the function body.

**How to fix:**
- add an explicit `reason_codes: list[str] | None = None` parameter so the signature is unambiguous

```
_result_from_plan(plan, status, **kwargs)
```

## Related Topics
- **Error**: Detailed error: `**kwargs` collides with explicit params of the same name
