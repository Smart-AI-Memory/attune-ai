---
type: faq
name: new-mcp-handlers-must-match-the-validation-pattern-of-adjacent
tags: [testing, security, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about new MCP handlers must match the validation pattern of adjacent handlers?

## Answer

`_run_test_generation` was the only handler (out of 10) missing `_validate_file_path()` — easy to miss because the handler worked fine without it. When adding a new MCP tool handler, copy the validation block from the nearest similar handler, not just the workflow call pattern.

```
_run_test_generation
```

## Related Topics
- **Error**: Detailed error: New MCP handlers must match the validation pattern of
  adjacent handlers
