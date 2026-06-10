---
type: tip
name: memory-tip
feature: memory
depth: tip
generated_at: 2026-06-10T07:07:04.799881+00:00
source_hash: 570dd4977cd655a0cf44a47b917577fd70f4cf08eb5d256d4da2915dbea871f0
status: generated
---

# Tip: working effectively with memory

Call `is_redis_available()` before you instantiate any Redis-backed component.

This single guard prevents import-time failures in environments where Redis is not installed — the function checks availability without importing the Redis subsystem at all. Skipping it means a missing dependency surfaces as a confusing runtime error instead of a clear unavailability signal.

**Why it works:** `is_redis_available()` is specifically designed for this pre-flight check, so you pay no import cost regardless of the result.

**Tradeoff:** You still need to handle the `False` case explicitly — the function tells you Redis is unavailable but does not fall back to a mock automatically. Use `get_redis_memory(use_mock=True)` if you want an automatic fallback.

## Source files

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
