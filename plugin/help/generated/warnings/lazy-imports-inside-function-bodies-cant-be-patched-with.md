---
type: warning
name: lazy-imports-inside-function-bodies-cant-be-patched-with
confidence: Verified
tags: [testing, imports, claude-code]
source: .claude/CLAUDE.md
---

# Warning: Lazy imports inside function bodies can't be patched with
  `patch("module.Name")`

## Condition

`HookEvent`, `HookRegistry`, and similar names imported inside function bodies are never bound at module scope

## Risk

`patch("attune.commands.context.HookEvent")` raises `AttributeError`

## Mitigation

1. Use `patch.dict("sys.modules", ...)` to simulate `ImportError`, or use the real value for happy-path tests

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Lazy imports inside function bodies can't be patched with
  `patch("module.Name")`
