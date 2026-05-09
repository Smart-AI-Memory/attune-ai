---
type: faq
name: clusterfuzzlite-no-deps-misses-transitive-imports
tags: [security, imports, packaging]
source: .claude/CLAUDE.md
---

# FAQ: Why do I get `ModuleNotFoundError` (clusterFuzzLite --no-deps misses transitive imports)?

## Answer

`.clusterfuzzlite/build.sh` used `pip3 install --no-deps` to keep the fuzz image lean, but when `attune.security` gained a transitive import chain to `structlog` (via `attune.memory.security.secrets_detector`), the fuzz target crashed at startup with `ModuleNotFoundError`. PyInstaller `--hidden-import` flags tell the bundler about modules but don't install missing packages.

**How to fix:**
- explicitly `pip3 install <dep>` for any dependency reachable from fuzz target imports

```
.clusterfuzzlite/build.sh
```

## Related Topics
- **Error**: Detailed error: ClusterFuzzLite `--no-deps` misses transitive imports
