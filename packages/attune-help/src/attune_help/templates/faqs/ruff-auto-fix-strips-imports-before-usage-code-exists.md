---
type: faq
name: ruff-auto-fix-strips-imports-before-usage-code-exists
tags: [imports, claude-code, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about ruff auto-fix strips imports before usage code exists?

## Answer

When adding `from mcp.server import Server` at the top of a file but the code using `Server(...)` is at the bottom (not yet written), ruff's `--fix` removes the import as unused. The edit succeeds but the import silently vanishes.

**How to fix:**
- add imports and their usage code in the same edit, or add usage first then imports

```
from mcp.server import Server
```

## Related Topics
- **Error**: Detailed error: Ruff auto-fix strips imports before usage code exists
