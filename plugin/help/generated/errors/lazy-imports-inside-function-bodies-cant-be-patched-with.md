---
type: error
name: lazy-imports-inside-function-bodies-cant-be-patched-with
confidence: Verified
tags: [testing, imports, claude-code]
source: .claude/CLAUDE.md
---

# Error: Lazy imports inside function bodies can't be patched with
  `patch("module.Name")`

## Signature

AttributeError

## Root Cause

`HookEvent`, `HookRegistry`, and similar names imported inside function bodies are never bound at module scope. `patch("attune.commands.context.HookEvent")` raises `AttributeError`. Use `patch.dict("sys.modules", ...)` to simulate `ImportError`, or use the real value for happy-path tests.

## Resolution

1. Use `patch.dict("sys.modules", ...)` to simulate `ImportError`, or use the real value for happy-path tests

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Lazy imports inside function bodies can't be patched with
  `patch("module.Name")`
- Tip: Best practice: Lazy imports inside function bodies can't be patched with
  `patch("module.Name")`
- Task: Update test mocks and assertions
