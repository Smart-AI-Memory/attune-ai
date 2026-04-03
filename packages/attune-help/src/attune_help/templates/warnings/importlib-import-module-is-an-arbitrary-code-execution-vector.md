---
type: warning
name: importlib-import-module-is-an-arbitrary-code-execution-vector
confidence: Verified
tags: [security, imports, claude-code]
source: .claude/CLAUDE.md
---

# Warning: `importlib.import_module()` is an arbitrary code execution
  vector

## Condition

The hook executor's `_execute_python()` fell through to `importlib.import_module(module_path)` for any module not in `_python_handlers`

## Risk

Ignoring this guidance may cause: `importlib.import_module()` is an arbitrary code execution
  vector

## Mitigation

1. allowlist module prefixes (e.g., `("attune.",)`) before the import call

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `importlib.import_module()` is an arbitrary code execution
  vector
