# Redis Holding Area

Temporary staging area for Redis modules being extracted
from attune-ai core into the standalone `attune-redis`
plugin.

## Purpose

These files are copies of the Redis modules that currently
live in `src/attune/`. They will move to the `attune-redis`
package in **Phase 2** of the Redis plugin plan.

Until then, the canonical versions remain in their
original locations under `src/attune/redis_memory*.py`.

## Files

| File | Original Location |
|------|------------------|
| `redis_auto_detect.py` | `src/attune/redis_auto_detect.py` |
| `redis_bootstrap.py` | `src/attune/redis_bootstrap.py` |
| `redis_config.py` | `src/attune/redis_config.py` |
| `redis_memory.py` | `src/attune/redis_memory.py` |
| `redis_memory_coordination.py` | `src/attune/redis_memory_coordination.py` |
| `redis_memory_models.py` | `src/attune/redis_memory_models.py` |
| `redis_memory_patterns.py` | `src/attune/redis_memory_patterns.py` |
| `redis_memory_storage.py` | `src/attune/redis_memory_storage.py` |

## Extraction Timeline

- **Phase 1 (complete):** Decouple imports, define
  `MemoryBackend` protocol, ensure core works without Redis
- **Phase 2 (in progress):** `attune_redis/` plugin created
  with `AMSMemoryBackend` wrapping Redis Agent Memory
  Server. These legacy modules will be replaced by the AMS
  wrapper — most are no longer needed.
- **Phase 3:** Add Redis-specific developer workflows
- **Phase 4:** Reference implementation

## Plan

See [attune-redis-plugin.md](../../.claude/plans/attune-redis-plugin.md)
for the full plan.

## Do Not

- Import from this directory — use `src/attune/redis_memory`
- Modify files here without updating the originals
- Delete this directory until Phase 2 extraction is complete
