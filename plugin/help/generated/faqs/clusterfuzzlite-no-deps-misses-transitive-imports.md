---
name: clusterfuzzlite-no-deps-misses-transitive-imports
source: .claude/CLAUDE.md
summary: This template explains how to resolve `ModuleNotFoundError` exceptions that
  occur when using `pip3 install --no-deps` in ClusterFuzzLite by explicitly installing
  all transitive dependencies required by your fuzz target.
tags:
- security
- imports
- packaging
type: faq
---

# FAQ: Why Do I Get `ModuleNotFoundError` When Using `--no-deps` in ClusterFuzzLite?

## Answer

The `.clusterfuzzlite/build.sh` script uses `pip3 install --no-deps` to keep the fuzz image lean. However, when `attune.security` gained a transitive import chain to `structlog` (via `attune.memory.security.secrets_detector`), the fuzz target crashed at startup with a `ModuleNotFoundError`.

> **Note:** PyInstaller `--hidden-import` flags inform the bundler about modules, but they do not install missing packages.

### Root Cause

`pip3 install --no-deps` skips all dependencies of the installed package. Any transitive dependency introduced later — one not explicitly listed in your build script — will be absent from the fuzz image at runtime.

### How to Fix

Explicitly install every dependency reachable from your fuzz target's import chain. Add a `pip3 install` call for each missing package directly in your build script:

```bash
# .clusterfuzzlite/build.sh

# Install the primary package without dependencies
pip3 install --no-deps attune.security

# Explicitly install required transitive dependencies
pip3 install structlog
```

To identify missing transitive dependencies before they cause runtime failures, inspect the full dependency tree:

```bash
pip3 install pipdeptree
pipdeptree -p attune.security
```

---

## Related Topics

- **Error Reference:** ClusterFuzzLite `--no-deps` misses transitive imports (`ModuleNotFoundError` at fuzz target startup)
