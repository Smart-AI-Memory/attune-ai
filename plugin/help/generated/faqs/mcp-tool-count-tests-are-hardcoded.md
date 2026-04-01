---
type: faq
name: mcp-tool-count-tests-are-hardcoded
tags: [testing, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about MCP tool count tests are hardcoded?

## Answer

When adding new MCP tools to `server.py`, grep tests for the old tool count (e.g., `assert len(tools) == 22`). The assertion in `test_mcp_memory_tools.py` is the main one but others may exist.

```
, grep tests for the old tool count (e.g.,
```

## Related Topics
- **Error**: Detailed error: MCP tool count tests are hardcoded
