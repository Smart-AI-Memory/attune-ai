---
type: error
name: adding-logger-before-eager-imports-triggers-e402-in-init-py
confidence: Verified
tags: [imports, python]
source: .claude/CLAUDE.md
---

# Error: Adding `logger` before eager imports triggers E402 in
  `__init__.py`

## Signature

Adding `logger` before eager imports triggers E402 in
  `__init__.py`

## Root Cause

Placing `logger = logging.getLogger(__name__)` between stdlib imports and eager `from .module import ...` lines makes ruff flag all subsequent relative imports as E402 (module-level import not at top). Move the logger assignment after ALL imports, just before the first non-import statement.

## Resolution

1. Move the logger assignment after ALL imports, just before the first non-import statement

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
