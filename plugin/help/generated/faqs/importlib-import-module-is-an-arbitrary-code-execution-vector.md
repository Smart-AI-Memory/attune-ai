---
type: faq
name: importlib-import-module-is-an-arbitrary-code-execution-vector
tags: [security, imports, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about importlib.import_module() is an arbitrary code execution vector?

## Answer

The hook executor's `_execute_python()` fell through to `importlib.import_module(module_path)` for any module not in `_python_handlers`. This allowed importing `os`, `subprocess`, or any installed package.

**How to fix:**
- allowlist module prefixes (e.g., `("attune.",)`) before the import call

```
_execute_python()
```

## Related Topics
- **Error**: Detailed error: `importlib.import_module()` is an arbitrary code execution
  vector
