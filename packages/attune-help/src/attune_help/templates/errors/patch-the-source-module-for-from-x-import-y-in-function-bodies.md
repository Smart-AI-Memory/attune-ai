---
type: error
name: patch-the-source-module-for-from-x-import-y-in-function-bodies
confidence: Verified
tags: [testing, security, imports]
source: .claude/CLAUDE.md
---

# Error: Patch the source module for `from ..X import Y` in function
  bodies

## Signature

Patch the source module for `from ..X import Y` in function
  bodies

## Root Cause

When a function does `from ..real_tools import RealSecurityAuditor`, patching `_strategies.base.RealSecurityAuditor` fails (not at module scope). Instead patch `real_tools.RealSecurityAuditor` — the source module where the name IS at module scope. The deferred import resolves from the (now-patched) source at call time. This is cleaner than moving imports or using `patch.dict("sys.modules")`.

## Resolution

1. When a function does `from ..real_tools import RealSecurityAuditor`, patching `_strategies.base.RealSecurityAuditor` fails (not at module scope)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
