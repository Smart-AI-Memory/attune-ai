---
type: tip
feature: memory
depth: tip
generated_at: 2026-04-14T15:06:58.444111+00:00
source_hash: becc5608c1ce3b9583965f538dce42193f013b114a01d1fbfa3234d4228db706
status: generated
---

# Tip: working effectively with memory

Use `is_redis_available()` before importing Redis dependencies to avoid import errors when Redis isn't installed. This graceful degradation pattern prevents crashes and enables mock backends for testing.

The memory module separates availability checks from actual Redis operations because Redis is an optional dependency. Import-time failures break the entire application, while runtime checks let you fall back to alternatives.

**Available checks:**
- `is_redis_available()` — Returns bool without importing Redis
- `check_redis_connection()` — Tests actual connectivity (imports Redis)
- Backend `is_connected()` method — Tests live connections

**Source files:** `src/attune/memory/**`

**Tags:** `memory`, `storage`
