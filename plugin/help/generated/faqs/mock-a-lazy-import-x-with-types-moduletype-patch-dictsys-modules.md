---
type: faq
name: mock-a-lazy-import-x-with-types-moduletype-patch-dictsys-modules
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about mock a lazy import X with types.ModuleType + patch.dict("sys.modules")?

## Answer

When a function body does `import attune` (bare module, not `from X import Y`), `patch("module.attune")` fails (not at module scope) and source-module patching doesn't apply. The lazy import inside the function resolves from `sys.modules`.

**How to fix:**
- create `mock = types.ModuleType("attune")`, set attributes like `mock.__version__ = "1.0.0"`, then use `patch.dict("sys.modules", {"attune": mock})`

```
import attune
```

## Related Topics
- **Error**: Detailed error: Mock a lazy `import X` with `types.ModuleType` +
  `patch.dict("sys.modules")`
