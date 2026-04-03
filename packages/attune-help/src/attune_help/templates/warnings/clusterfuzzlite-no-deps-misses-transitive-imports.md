---
type: warning
name: clusterfuzzlite-no-deps-misses-transitive-imports
confidence: Verified
tags: [security, imports, packaging]
source: .claude/CLAUDE.md
---

# Warning: ClusterFuzzLite `--no-deps` misses transitive imports

## Condition

`.clusterfuzzlite/build.sh` used `pip3 install --no-deps` to keep the fuzz image lean, but when `attune.security` gained a transitive import chain to `structlog` (via `attune.memory.security.secrets_detector`), the fuzz target crashed at startup with `ModuleNotFoundError`

## Risk

`.clusterfuzzlite/build.sh` used `pip3 install --no-deps` to keep the fuzz image lean, but when `attune.security` gained a transitive import chain to `structlog` (via `attune.memory.security.secrets_detector`), the fuzz target crashed at startup with `ModuleNotFoundError`

## Mitigation

1. explicitly `pip3 install <dep>` for any dependency reachable from fuzz target imports

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: ClusterFuzzLite `--no-deps` misses transitive imports
