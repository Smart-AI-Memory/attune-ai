---
type: error
name: patch-requires-the-target-name-to-exist-at-module-scope-at
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Error: `patch()` requires the target name to exist at module scope at
  patch time

## Signature

AttributeError

## Root Cause

`unittest.mock.patch("module.Name")` fails with `AttributeError` if `Name` is only imported inside a function body (lazy/deferred import). The mock library looks up the attribute on the module object immediately when the patch context is entered. Move any import that needs to be patchable to module level — even optional ones, using an availability guard pattern if needed.

## Resolution

1. Move any import that needs to be patchable to module level — even optional ones, using an availability guard pattern if needed

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
