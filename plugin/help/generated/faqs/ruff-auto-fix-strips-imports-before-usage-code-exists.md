---
type: faq
name: ruff-auto-fix-strips-imports-before-usage-code-exists
tags: [imports, claude-code, python]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Ruff auto-fix strips imports before usage code exists?

## Answer

When adding `from mcp.server import Server` at the top of a file but the code using `Server(...)` is at the bottom (not yet written), ruff's `--fix` removes the import as unused. The edit succeeds but the import silently vanishes.


**Fix:**

- add imports and their usage code in the same edit, or add usage first then imports

```
from mcp.server import Server
```

## Related Topics
- **Error**: Detailed error: Ruff auto-fix strips imports before usage code exists
