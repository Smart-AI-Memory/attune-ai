---
name: new-mcp-handlers-must-match-the-validation-pattern-of-adjacent
source: .claude/CLAUDE.md
summary: This template explains that all new MCP tool handlers must include `_validate_file_path()`
  validation calls to match the established pattern of existing handlers, even though
  handlers can function without it, because working behavior does not guarantee correct
  or secure behavior.
tags:
- testing
- security
- claude-code
type: faq
---

# FAQ: New MCP Handlers Must Match the Validation Pattern of Adjacent Handlers

## Answer

When adding a new MCP tool handler, every handler must include a `_validate_file_path()` call — not just the workflow invocation pattern.

This is easy to miss because the handler will work correctly without it. For example, `_run_test_generation` was the only handler out of 10 that was missing `_validate_file_path()`, and it functioned normally until the missing validation check was caught.

**When creating a new handler, copy the full validation block from the nearest similar handler**, not just the workflow call pattern:

```python
_run_test_generation
```

## Key Takeaway

Working behavior does not guarantee correct behavior. A handler that skips `_validate_file_path()` will appear functional but is inconsistent with the established pattern and may fail validation checks or security requirements downstream.

## Related Topics

- **Error:** `New MCP handlers must match the validation pattern of adjacent handlers`
