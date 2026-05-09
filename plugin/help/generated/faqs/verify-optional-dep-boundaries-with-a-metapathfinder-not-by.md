---
type: faq
name: verify-optional-dep-boundaries-with-a-metapathfinder-not-by
tags: [imports, packaging, python]
source: .claude/CLAUDE.md
---

# FAQ: Why do I get `ImportError` (verify optional dep boundaries with a MetaPathFinder, not by uninstalling)?

## Answer

To prove a package imports cleanly without an optional dep, install a custom finder on `sys.meta_path` that raises `ImportError` for the target module name, then attempt the imports. Cleaner than `pip uninstall` (which mutates the venv), faster than spinning up a fresh venv, and the same script works in CI.

```
sys.meta_path
```

## Related Topics
- **Error**: Detailed error: Verify optional dep boundaries with a `MetaPathFinder`,
  not by uninstalling
