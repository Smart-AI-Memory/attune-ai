---
type: faq
name: patch-requires-the-target-name-to-exist-at-module-scope-at
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# FAQ: Why do I get `AttributeError` (patch() requires the target name to exist at module scope at patch time)?

## Answer

`unittest.mock.patch("module.Name")` fails with `AttributeError` if `Name` is only imported inside a function body (lazy/deferred import). The mock library looks up the attribute on the module object immediately when the patch context is entered.

```
unittest.mock.patch("module.Name")
```

## Related Topics
- **Error**: Detailed error: `patch()` requires the target name to exist at module scope at
  patch time
