---
type: error
name: verify-optional-dep-boundaries-with-a-metapathfinder-not-by
confidence: Verified
tags: [imports, packaging, python]
source: .claude/CLAUDE.md
---

# Error: Verify optional dep boundaries with a `MetaPathFinder`,
  not by uninstalling

## Signature

ImportError

## Root Cause

To prove a package imports cleanly without an optional dep, install a custom finder on `sys.meta_path` that raises `ImportError` for the target module name, then attempt the imports. Cleaner than `pip uninstall` (which mutates the venv), faster than spinning up a fresh venv, and the same script works in CI. Pattern: ```python class Block:     def find_module(self, name, path=None):         if name == "target_pkg" or name.startswith("target_pkg."):             return self     def load_module(self, name):         raise ImportError(f"BLOCKED: {name}") sys.meta_path.insert(0, Block()) import my_pkg  # should succeed ```

## Resolution

1. To prove a package imports cleanly without an optional dep, install a custom finder on `sys.meta_path` that raises `ImportError` for the target module name, then attempt the imports

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
