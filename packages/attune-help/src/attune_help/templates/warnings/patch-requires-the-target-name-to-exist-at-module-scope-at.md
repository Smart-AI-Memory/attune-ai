---
type: warning
name: patch-requires-the-target-name-to-exist-at-module-scope-at
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Warning: `patch()` requires the target name to exist at module scope at
  patch time

## Condition

`unittest.mock.patch("module.Name")` fails with `AttributeError` if `Name` is only imported inside a function body (lazy/deferred import)

## Risk

`unittest.mock.patch("module.Name")` fails with `AttributeError` if `Name` is only imported inside a function body (lazy/deferred import)

## Mitigation

1. Move any import that needs to be patchable to module level — even optional ones, using an availability guard pattern if needed

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `patch()` requires the target name to exist at module scope at
  patch time
