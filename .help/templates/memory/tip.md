---
type: tip
name: memory-tip
feature: memory
depth: tip
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 7d6a88f7e825fe56e3b06e3bce6dd904fe6a75cd1c13a3a134e4b44138df245e
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
