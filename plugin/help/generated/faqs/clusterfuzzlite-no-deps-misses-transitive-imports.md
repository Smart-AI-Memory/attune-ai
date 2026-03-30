---
type: faq
name: clusterfuzzlite-no-deps-misses-transitive-imports
tags: [security, imports, packaging]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: ClusterFuzzLite `--no-deps` misses transitive imports?

## Answer

`.clusterfuzzlite/build.sh` used `pip3 install --no-deps` to keep the fuzz image lean, but when `attune.security` gained a transitive import chain to `structlog` (via `attune.memory.security.secrets_detector`), the fuzz target crashed at startup with `ModuleNotFoundError`. PyInstaller `--hidden-import` flags tell the bundler about modules but don't install missing packages.


**Fix:**

- explicitly `pip3 install <dep>` for any dependency reachable from fuzz target imports

```
.clusterfuzzlite/build.sh
```

## Related Topics
- **Error**: Detailed error: ClusterFuzzLite `--no-deps` misses transitive imports
