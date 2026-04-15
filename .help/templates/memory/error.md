---
type: error
feature: memory
depth: error
generated_at: 2026-04-14T15:05:43.110764+00:00
source_hash: becc5608c1ce3b9583965f538dce42193f013b114a01d1fbfa3234d4228db706
status: generated
---

# Memory errors

This page covers failures in Attune AI's memory subsystem, which handles short-term storage, Claude memory integration, long-term pattern storage, and control panel operations.

## Common error signatures

- **`OSError: REDIS_URL not found`** — Raised by `get_railway_redis()` when Redis environment variables are missing on Railway deployments
- **`MemoryPermissionError`** — Access denied for classified patterns or restricted memory operations
- **`SecurityError`** — Pattern classification or encryption failures in secure memory operations
- **`FileNotFoundError`** — Missing CLAUDE.md files during memory loading or invalid storage directories
- **`ConnectionError`** — Redis connection failures or backend unavailability
- **`ValueError`** — Invalid Redis URL format or malformed memory configuration

## Where errors originate

Memory failures typically start in these key functions:

- **`get_railway_redis()`** — Fails when `REDIS_URL` environment variable is missing on Railway deployments
- **`get_redis_memory()`** — Connection errors when Redis backend is unavailable or misconfigured
- **`ClaudeMemoryLoader.load_all_memory()`** — File system errors when CLAUDE.md files are missing or unreadable
- **`MemoryControlPanel.start_redis()`** — Process startup failures when Redis cannot be launched locally
- **`SecureMemDocsIntegration`** operations — Permission errors when accessing classified patterns without proper authorization

## How to diagnose

1. **Check Redis connectivity first.** Run `check_redis_connection()` to verify your Redis backend is accessible. Connection failures are the most common cause of memory errors.

2. **Verify environment variables for Railway deployments.** If you see "REDIS_URL not found", ensure Redis is added to your Railway project with `railway add --database redis`.

3. **Inspect memory file permissions.** When `ClaudeMemoryLoader` fails, check that CLAUDE.md files exist and are readable at the expected paths (`enterprise_memory_path`, project root).

4. **Review classification errors in secure operations.** `SecurityError` and `MemoryPermissionError` indicate pattern access violations — check if your operation requires higher privilege levels or different classification rules.

5. **Enable debug logging for detailed tracing.** Set logging level to `DEBUG` before calling memory operations to see connection attempts, file loading sequences, and permission checks.

## Source files

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
