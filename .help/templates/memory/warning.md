---
type: warning
feature: memory
depth: warning
generated_at: 2026-04-14T15:05:57.526210+00:00
source_hash: becc5608c1ce3b9583965f538dce42193f013b114a01d1fbfa3234d4228db706
status: generated
---

# Memory cautions

## What to watch for

The memory subsystem handles storage, retrieval, and security for AI agents. Redis connections, file loading, and cross-session coordination introduce several risks that can cause data loss or security breaches.

## Risk areas

### Redis connection failures masquerading as success

`is_redis_available()` returns true even when Redis is installed but not running. This leads to false positives where your code assumes Redis is ready but connection attempts later fail silently. Always pair this check with an actual connection test using `check_redis_connection()`.

### Claude memory file import loops

`ClaudeMemoryLoader.load_all_memory()` follows import statements between CLAUDE.md files. Circular imports create infinite loops that consume memory until the process crashes. The `max_import_depth` setting (default 5) provides some protection, but deeply nested legitimate imports can still trigger the limit unexpectedly.

### Cross-session memory conflicts

Multiple agents sharing Redis storage can overwrite each other's data if they use the same keys. The `agent_id` parameter in `MemoryBackend.stash()` is optional, making it easy to forget. Without it, agents step on each other's temporary data, causing intermittent failures that are hard to debug.

### Encryption key rotation breaks existing data

The `EncryptionManager` encrypts sensitive patterns but doesn't handle key rotation. If you change encryption keys, previously stored data becomes permanently unreadable. There's no migration path built into the system.

### Railway deployment Redis URL confusion

`get_railway_redis()` expects `REDIS_URL` but Railway's web interface shows `REDIS_PUBLIC_URL`. Using the wrong environment variable causes connection failures with a misleading error message about Redis not being added to your project.

## How to avoid problems

1. **Always verify Redis connectivity before storing data.** Call `check_redis_connection()` and handle the failure case explicitly rather than relying on `is_redis_available()`.

2. **Set explicit agent IDs for all memory operations.** Generate unique IDs using `generate_agent_id()` and pass them to every `stash()`, `retrieve()`, and `delete()` call.

3. **Validate CLAUDE.md imports before loading.** Check for circular references in your memory files manually or write a pre-load validation script.

4. **Test encryption scenarios with key changes.** If you use encrypted storage, verify that changing keys doesn't break your application permanently.

5. **Use Railway's correct Redis environment variables.** For Railway deployments, use `REDIS_URL` for internal connections and only use `REDIS_PUBLIC_URL` for external debugging.

## Source files

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
