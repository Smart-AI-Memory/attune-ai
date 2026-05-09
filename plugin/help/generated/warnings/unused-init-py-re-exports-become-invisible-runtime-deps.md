---
type: warning
name: unused-init-py-re-exports-become-invisible-runtime-deps
confidence: Verified
tags: [testing, imports, claude-code]
source: .claude/CLAUDE.md
---

# Warning: Unused `__init__.py` re-exports become invisible
  runtime deps

## Condition

Adding `from sibling_pkg.foo import Bar` to a package's `__init__.py` for "backward compat" makes that package fail to import unless `sibling_pkg` is installed — even if NO consumer actually imports `Bar` from your package

## Risk

Adding `from sibling_pkg.foo import Bar` to a package's `__init__.py` for "backward compat" makes that package fail to import unless `sibling_pkg` is installed — even if NO consumer actually imports `Bar` from your package

## Mitigation

1. Adding `from sibling_pkg.foo import Bar` to a package's `__init__.py` for "backward compat" makes that package fail to import unless `sibling_pkg` is installed — even if NO consumer actually imports `Bar` from your package
2. Before adding any cross-package re-export, grep `src/`, `plugin/`, and `tests/` for actual consumers of the re-exported names

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Unused `__init__.py` re-exports become invisible
  runtime deps
