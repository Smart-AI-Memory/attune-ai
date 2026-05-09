---
type: faq
name: metapathfinder-find-module-load-module-is-dead-in-python-3-12
tags: [ci, testing, imports, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: Why do I get `ImportError` (metaPathFinder find_module/load_module is dead in Python 3.12+ — use sys.modules[name] = None sentinel instead)?

## Answer

The existing "Verify optional dep boundaries with a MetaPathFinder" lesson is partially wrong. The deprecated `find_module` / `load_module` hooks stopped firing in 3.12's import machinery (which migrated to `find_spec`/`create_module`/`exec_module` fully).

```
find_module
```

## Related Topics
- **Error**: Detailed error: MetaPathFinder `find_module`/`load_module` is dead in
  Python 3.12+ — use `sys.modules[name] = None` sentinel
  instead
