---
type: troubleshooting
feature: memory
depth: troubleshooting
generated_at: 2026-04-14T15:06:15.251972+00:00
source_hash: becc5608c1ce3b9583965f538dce42193f013b114a01d1fbfa3234d4228db706
status: generated
---

# Troubleshoot memory

## Before you start

The Attune AI memory subsystem handles storage, retrieval, and security across short-term Redis backends, Claude memory files, and long-term pattern storage.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Memory operations fail silently | Call `backend.is_connected()` to verify Redis connectivity |
| Claude memory files not loading | Verify `.claude/CLAUDE.md` exists and `config.enabled = True` |
| Redis connection errors | Run `check_redis_connection()` to test connection parameters |
| Memory API returns 500 errors | Check if Redis is running with `panel.start_redis()` |
| Stale or missing cached data | Call `backend.get_stats()` to inspect TTL and key counts |
| Permission denied on memory operations | Verify API key authentication with `APIKeyAuth.is_valid()` |

## Step-by-step diagnosis

1. **Test the memory backend connection.**
   Start by verifying the underlying storage is accessible:
   ```python
   from attune.memory import is_redis_available, check_redis_connection

   # Quick availability check
   if not is_redis_available():
       print("Redis module not available")

   # Detailed connection test
   status = check_redis_connection()
   print(f"Redis status: {status}")
   ```

2. **Verify configuration and environment.**
   Memory components rely on environment variables and config files:
   ```python
   from attune.memory.config import get_redis_config

   config = get_redis_config()
   print(f"Redis config: {config}")

   # Check for Railway deployment
   import os
   if 'REDIS_URL' in os.environ:
       print(f"Redis URL configured: {os.environ['REDIS_URL'][:20]}...")
   ```

3. **Test basic memory operations.**
   Isolate the failure with minimal backend operations:
   ```python
   from attune.memory.config import get_redis_memory

   memory = get_redis_memory()

   # Test basic storage and retrieval
   success = memory.stash("test_key", "test_value", ttl=60)
   print(f"Stash successful: {success}")

   retrieved = memory.retrieve("test_key")
   print(f"Retrieved: {retrieved}")

   stats = memory.get_stats()
   print(f"Backend stats: {stats}")
   ```

4. **Debug Claude memory loading.**
   If Claude memory files aren't loading:
   ```python
   from attune.memory.claude_memory import ClaudeMemoryLoader, ClaudeMemoryConfig

   config = ClaudeMemoryConfig(enabled=True, validate_files=True)
   loader = ClaudeMemoryLoader(config)

   try:
       content = loader.load_all_memory("./")
       files = loader.get_loaded_files()
       print(f"Loaded {len(files)} memory files")
   except Exception as e:
       print(f"Loading failed: {e}")
   ```

5. **Check control panel and API status.**
   For Memory Control Panel issues:
   ```python
   from attune.memory.control_panel import MemoryControlPanel

   panel = MemoryControlPanel()
   status = panel.status()
   health = panel.health_check()

   print(f"Panel status: {status}")
   print(f"Health check: {health}")
   ```

## Common fixes

- **Redis connection failures:** Set the `REDIS_URL` environment variable or ensure Redis is running on localhost:6379. For Railway deployments, run `railway add --database redis` if the URL is missing.

- **Memory files not found:** Run `create_default_project_memory("./")` to generate a starter `.claude/CLAUDE.md` file, or verify the project root path in `ClaudeMemoryConfig.project_root`.

- **Permission errors in enterprise features:** Check that your API key is configured correctly in `APIKeyAuth` and that rate limiting isn't blocking requests.

- **Stale cache data:** Clear the memory backend with `backend.delete(key)` for specific keys or `panel.clear_short_term()` for bulk clearing.

- **Memory API server won't start:** Ensure the port (default 8765) isn't in use and Redis is accessible. Use `panel.start_redis()` to launch Redis if `auto_start_redis=True` in your config.

- **Import errors:** The memory system has optional Redis dependencies. Install with `pip install attune[redis]` or use mock backends for development with `get_redis_memory(use_mock=True)`.

## Source files

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
