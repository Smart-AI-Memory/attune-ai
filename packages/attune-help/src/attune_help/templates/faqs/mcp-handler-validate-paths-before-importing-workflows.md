---
type: faq
name: mcp-handler-validate-paths-before-importing-workflows
tags: [security, imports, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about MCP handler: validate paths before importing workflows?

## Answer

In `server.py`, `_validate_file_path()` must run before the lazy `from attune.workflows.X import XWorkflow` import. If the import fails (wrong class name, missing dep), the path validation never fires and the security check is bypassed.

**How to fix:**
- Always: validate first, import second

```
_validate_file_path()
```

## Related Topics
- **Error**: Detailed error: MCP handler: validate paths before importing workflows
