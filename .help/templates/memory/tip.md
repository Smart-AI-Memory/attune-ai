---
type: tip
name: memory-tip
feature: memory
depth: tip
generated_at: 2026-05-16T06:14:13.803950+00:00
source_hash: 54f52a79be1ecfe32e99b4f09f84bda845815a0129b603c252aa4c74c2e1a61c
status: generated
---

# Tip: Use `is_redis_available()` before constructing a memory backend

Call `is_redis_available()` before you call `get_redis_memory()` or `get_railway_redis()`. It checks whether the Redis subsystem is importable and reachable without triggering a heavy import chain — so a missing or unreachable Redis instance fails fast and clearly instead of raising deep inside a constructor.

**Why it sticks:** a one-line guard at startup is cheaper than debugging a `ConnectionRefusedError` mid-session.

**Tradeoff:** `is_redis_available()` is a lightweight probe, not a guaranteed health check. A Redis instance that passes the probe can still become unavailable between the check and your first `stash()` call. For production reliability, also wire up `MemoryControlPanel.health_check()` and handle `MemoryBackend.is_connected()` returning `False` at runtime.

## Source files

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
