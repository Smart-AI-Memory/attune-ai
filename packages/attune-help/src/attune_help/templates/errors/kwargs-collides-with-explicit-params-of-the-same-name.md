---
type: error
name: kwargs-collides-with-explicit-params-of-the-same-name
confidence: Verified
tags: [python]
source: .claude/CLAUDE.md
---

# Error: `**kwargs` collides with explicit params of the same name

## Signature

`**kwargs` collides with explicit params of the same name

## Root Cause

If a helper like `_result_from_plan(plan, status, **kwargs)` builds a dataclass and callers pass `reason_codes=...` in `**kwargs`, it silently conflicts with any `reason_codes=...` already set inside the function body.

## Resolution

1. add an explicit `reason_codes: list[str] | None = None` parameter so the signature is unambiguous

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
