---
type: tip
name: memory-tip
feature: memory
depth: tip
generated_at: 2026-06-04T23:45:26.869984+00:00
source_hash: c6803543f79e6bd38c2393239d6731920690afcab986165d0ce938b8ba0d5c25
status: generated
---

# Tip: working effectively with memory

Call `is_redis_available()` before you instantiate any Redis-backed component — it checks whether the Redis subsystem is importable and reachable without triggering an import error if Redis is absent. This one call prevents the most common memory initialization failures.

**Why it's worth the extra line:** Redis availability is an environment concern, not a code concern. Checking it explicitly at startup makes failures visible immediately rather than surfacing as a confusing `OSError` deep in `get_railway_redis()` or as silent no-ops in `stash()`.

**Tradeoff:** `is_redis_available()` does not validate your connection URL or credentials — it only confirms the subsystem is importable. Follow it with `check_redis_connection()` if you need a full connectivity check, and use `get_redis_memory()` (which reads environment variables) rather than constructing connection parameters by hand.

**Tags:** `memory`, `storage`
