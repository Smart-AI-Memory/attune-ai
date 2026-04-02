---
type: error
name: clusterfuzzlite-no-deps-misses-transitive-imports
confidence: Verified
tags: [security, imports, packaging]
source: .claude/CLAUDE.md
---

# Error: ClusterFuzzLite `--no-deps` misses transitive imports

## Signature

ModuleNotFoundError

## Root Cause

`.clusterfuzzlite/build.sh` used `pip3 install --no-deps` to keep the fuzz image lean, but when `attune.security` gained a transitive import chain to `structlog` (via `attune.memory.security.secrets_detector`), the fuzz target crashed at startup with `ModuleNotFoundError`. PyInstaller `--hidden-import` flags tell the bundler about modules but don't install missing packages.

## Resolution

1. explicitly `pip3 install <dep>` for any dependency reachable from fuzz target imports

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: ClusterFuzzLite `--no-deps` misses transitive imports
- Tip: Best practice: ClusterFuzzLite `--no-deps` misses transitive imports
