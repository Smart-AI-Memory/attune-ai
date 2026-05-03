---
name: silent-pass-blocks-in-discovery-registry-code-hide-import
source: .claude/CLAUDE.md
summary: This developer help template explains how to diagnose and fix `ImportError`
  exceptions that are silently suppressed by `pass` blocks in workflow discovery code,
  and demonstrates replacing them with explicit warning logs to surface import failures.
tags:
- imports
type: faq
---

# FAQ: Why Do I Get `ImportError`? (Silent `pass` Blocks in Discovery/Registry Code Hide Import Failures)

## Answer

Workflow discovery previously contained silent `pass` blocks that swallowed `ImportError` and `AttributeError` exceptions. When a workflow disappeared from `attune workflow list`, no diagnostic output was produced at any log level, making the root cause impossible to identify without inspecting the source code directly.

**Root cause:** Six `pass` blocks in the discovery and registry code silently suppressed import failures instead of logging them.

**How to fix:**

Replace silent `pass` blocks in discovery paths with explicit warning calls so that failures surface during `--verbose` output or log inspection:

```python
# Before — failure is silently ignored
try:
    import my_workflow
except ImportError:
    pass

# After — failure is logged for diagnosis
try:
    import my_workflow
except ImportError:
    logger.warning("Failed to import workflow 'my_workflow'", exc_info=True)
```

Always use `logger.warning()` (or higher) in discovery paths to ensure import errors are visible without requiring a code change or debugger.

## Related Topics

- **Error reference:** Silent `pass` blocks in discovery/registry code hide import failures
- **Configuration:** Enabling verbose logging with `--verbose` to surface suppressed errors
- **Best practices:** Exception handling patterns in workflow discovery and plugin registration
