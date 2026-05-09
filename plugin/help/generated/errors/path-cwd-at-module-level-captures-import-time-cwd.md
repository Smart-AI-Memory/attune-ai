---
type: error
name: path-cwd-at-module-level-captures-import-time-cwd
confidence: Verified
tags: [imports, python]
source: .claude/CLAUDE.md
---

# Error: `Path.cwd()` at module level captures import-time cwd

## Signature

`Path.cwd()` at module level captures import-time cwd

## Root Cause

`_DEFAULT = Path.cwd() / ".help"` evaluated at import time becomes stale if the working directory changes or the module is imported from a different cwd. Compute lazily inside the function: `Path(arg) if arg else Path.cwd() / ".help"`.

## Resolution

1. `_DEFAULT = Path.cwd() / ".help"` evaluated at import time becomes stale if the working directory changes or the module is imported from a different cwd

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
