---
type: faq
name: path-cwd-at-module-level-captures-import-time-cwd
tags: [imports, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about path.cwd() at module level captures import-time cwd?

## Answer

`_DEFAULT = Path.cwd() / ".help"` evaluated at import time becomes stale if the working directory changes or the module is imported from a different cwd. Compute lazily inside the function: `Path(arg) if arg else Path.cwd() / ".help"`.

```
_DEFAULT = Path.cwd() / ".help"
```

## Related Topics
- **Error**: Detailed error: `Path.cwd()` at module level captures import-time cwd
