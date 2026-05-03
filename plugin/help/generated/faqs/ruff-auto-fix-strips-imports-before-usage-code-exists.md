---
name: ruff-auto-fix-strips-imports-before-usage-code-exists
source: .claude/CLAUDE.md
summary: This template explains how Ruff's auto-fix feature removes imports that appear
  unused because their corresponding usage code hasn't been written yet, and provides
  strategies to prevent this issue.
tags:
- imports
- claude-code
- python
type: faq
---

# FAQ: Ruff Auto-Fix Removes Imports Before Usage Code Exists

## Answer

When you add an import such as `from mcp.server import Server` at the top of a file, but the code that uses `Server(...)` hasn't been written yet, Ruff's `--fix` flag will treat the import as unused and silently remove it. The edit appears to succeed, but the import is gone.

**Example of the problem:**

```python
# Import added at the top...
from mcp.server import Server

# ...but Server(...) usage not yet written at the bottom
```

**How to avoid this:**

- Add the import and its usage code in the **same edit**, so Ruff can see the import is referenced.
- Alternatively, write the usage code **first**, then add the import in a subsequent edit.

> **Note:** This is expected Ruff behavior — it removes any import it cannot find a reference to at the time `--fix` runs.

## Related Topics

- **Error Reference**: Ruff auto-fix strips imports before usage code exists
