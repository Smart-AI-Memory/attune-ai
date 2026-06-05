---
type: error
name: memory-error
feature: memory
depth: error
generated_at: 2026-06-04T23:45:26.852876+00:00
source_hash: c6803543f79e6bd38c2393239d6731920690afcab986165d0ce938b8ba0d5c25
status: generated
---

# Memory errors

## Common error signatures

Failures in the memory subsystem fall into three categories: Redis connectivity errors, file-loading errors for `CLAUDE.md` memory files, and security/permission violations.

- **`OSError: REDIS_URL not found. Make sure Redis is added to your Railway project.\nRun: railway add --database redis\nFor external access, use REDIS_PUBLIC_URL`** — raised by `get_railway_redis()` when the `REDIS_URL` environment variable is absent. The fix is to provision a Redis database in your Railway project before calling this function.

- **Connection failure from `is_redis_available()`** — returns `False` (rather than raising) when the Redis subsystem cannot be imported or contacted. If code that depends on Redis proceeds without checking this return value, subsequent calls to `get_redis_memory()` or `MemoryBackend.stash()` will fail with connection-level exceptions.

- **`MemoryPermissionError` / `SecurityError`** — raised when an operation violates classification rules or access-tier checks. These can occur during `MemoryControlPanel.delete_pattern()` or when `SecureMemDocsIntegration` enforces `Classification` rules on stored patterns.

- **`ShortTermSecurityError`** — raised by Redis-backed short-term memory operations when a security constraint (for example, PII detection or secrets scanning) blocks a `stash()` call.

- **`ValueError` from `parse_redis_url()`** — raised when the URL string passed to `parse_redis_url()` does not conform to the expected Redis URL format.

- **File-load failure in `ClaudeMemoryLoader.load_all_memory()`** — occurs when a `CLAUDE.md` file exceeds `ClaudeMemoryConfig.max_file_size_bytes` (default: 1,000,000 bytes), when `ClaudeMemoryConfig.max_import_depth` (default: 5) is exceeded by nested `@import` chains, or when `ClaudeMemoryConfig.validate_files` is `True` and a file fails validation.

## Where errors originate

The following functions are the primary failure points. Trace your exception back to one of these call sites to identify the root cause.

- **`get_railway_redis()`** — raises `OSError` when `REDIS_URL` is not set. Only call this function inside a Railway deployment after confirming Redis is provisioned.
- **`parse_redis_url(url)`** — raises `ValueError` on a malformed URL. Check the URL string before passing it in, or catch `ValueError` and log the bad value.
- **`get_redis_memory(url, use_mock)`** — wraps `parse_redis_url()` and environment variable lookup. A failure here means either a bad URL or a missing environment variable. Set `use_mock=True` to bypass Redis for local development.
- **`is_redis_available()`** — returns `False` rather than raising; callers that ignore this return value and proceed with Redis operations will encounter downstream failures.
- **`create_default_project_memory(project_root, framework)`** — writes `.claude/CLAUDE.md` to disk. Fails with `OSError` if the path is not writable or the directory cannot be created.
- **`ClaudeMemoryLoader.load_all_memory(project_root)`** — fails silently or raises when files exceed size/depth limits configured in `ClaudeMemoryConfig`.
- **`MemoryControlPanel.delete_pattern(pattern_id, user_id)`** — raises `MemoryPermissionError` if the calling `user_id` lacks the required access tier for the pattern's `Classification`.

## How to diagnose

1. **Check the exception type first.** `OSError` points to Redis connectivity or filesystem problems. `MemoryPermissionError` or `SecurityError` points to classification enforcement. `ValueError` points to a malformed Redis URL. The type tells you which subsystem to investigate.

2. **For Redis errors**, call `check_redis_connection()` to get a status dict describing the connection state, then verify that `is_redis_available()` returns `True` before proceeding. For Railway deployments, confirm the `REDIS_URL` environment variable is set.

3. **For `ClaudeMemoryLoader` failures**, inspect your `ClaudeMemoryConfig`: check `max_file_size_bytes`, `max_import_depth`, and `validate_files`. Call `ClaudeMemoryLoader.get_loaded_files()` after `load_all_memory()` to see which files were successfully loaded, then compare against the files you expected.

4. **For permission and security errors**, check the `Classification` assigned to the pattern and the `user_id` passed to the operation. `MemoryPermissionError` and `SecurityError` are exported from `__all__` and can be caught specifically — avoid catching the broad `Exception` base class, which would also hide unrelated bugs.

5. **Enable `DEBUG` logging.** The memory subsystem uses Python's `logging` module. Most raised exceptions are preceded by a `logger.error` or `logger.exception` call that records the state before the failure. Bumping the log level to `DEBUG` often reveals the proximate cause without needing to reproduce the error in a debugger.

## Source files

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
