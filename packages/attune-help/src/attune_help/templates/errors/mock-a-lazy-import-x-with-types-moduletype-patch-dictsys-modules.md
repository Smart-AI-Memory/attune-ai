---
type: error
name: mock-a-lazy-import-x-with-types-moduletype-patch-dictsys-modules
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Error: Mock a lazy `import X` with `types.ModuleType` +
  `patch.dict("sys.modules")`

## Signature

)` fails (not at module scope) and source-module patching doesn't apply. Fix: create `mock = types.ModuleType(

## Root Cause

When a function body does `import attune` (bare module, not `from X import Y`), `patch("module.attune")` fails (not at module scope) and source-module patching doesn't apply.

## Resolution

1. create `mock = types.ModuleType("attune")`, set attributes like `mock.__version__ = "1.0.0"`, then use `patch.dict("sys.modules", {"attune": mock})`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Mock a lazy `import X` with `types.ModuleType` +
  `patch.dict("sys.modules")`
- Task: Update test mocks and assertions
