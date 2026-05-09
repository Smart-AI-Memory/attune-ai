---
type: error
name: unused-init-py-re-exports-become-invisible-runtime-deps
confidence: Verified
tags: [testing, imports, claude-code]
source: .claude/CLAUDE.md
---

# Error: Unused `__init__.py` re-exports become invisible
  runtime deps

## Signature

Unused `__init__.py` re-exports become invisible
  runtime deps

## Root Cause

Adding `from sibling_pkg.foo import Bar` to a package's `__init__.py` for "backward compat" makes that package fail to import unless `sibling_pkg` is installed — even if NO consumer actually imports `Bar` from your package. The cost is paid at import time, not use time. Before adding any cross-package re-export, grep `src/`, `plugin/`, and `tests/` for actual consumers of the re-exported names. If nothing consumes them, delete the re-exports rather than carrying a hidden dependency.

## Resolution

1. Adding `from sibling_pkg.foo import Bar` to a package's `__init__.py` for "backward compat" makes that package fail to import unless `sibling_pkg` is installed — even if NO consumer actually imports `Bar` from your package

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Unused `__init__.py` re-exports become invisible
  runtime deps
- Task: Update test mocks and assertions
