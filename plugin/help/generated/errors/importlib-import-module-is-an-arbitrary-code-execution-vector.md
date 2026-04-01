---
type: error
name: importlib-import-module-is-an-arbitrary-code-execution-vector
confidence: Verified
tags: [security, imports, claude-code]
source: .claude/CLAUDE.md
---

# Error: `importlib.import_module()` is an arbitrary code execution
  vector

## Signature

`importlib.import_module()` is an arbitrary code execution
  vector

## Root Cause

The hook executor's `_execute_python()` fell through to `importlib.import_module(module_path)` for any module not in `_python_handlers`. This allowed importing `os`, `subprocess`, or any installed package.

## Resolution

1. allowlist module prefixes (e.g., `("attune.",)`) before the import call

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `importlib.import_module()` is an arbitrary code execution
  vector
