---
type: error
name: memory-error
feature: memory
depth: error
generated_at: 2026-05-16T06:14:13.789040+00:00
source_hash: 54f52a79be1ecfe32e99b4f09f84bda845815a0129b603c252aa4c74c2e1a61c
status: generated
---

# Memory errors

## Common error signatures

Failures in the memory subsystem fall into three categories: Redis connectivity, CLAUDE.md file loading, and security/permission violations.

**Redis connectivity**

- `OSError: REDIS_URL not found. Make sure Redis is added to your Railway project.\nRun: railway add --database redis\nFor external access, use REDIS_PUBLIC_URL` — raised by `get_railway_redis()` when the `REDIS_URL` environment variable is absent. Add Redis to your Railway project or set `REDIS_URL` before calling this function.
- `MemoryBackend.is_connected()` returns `False` — the backend initialized but cannot reach Redis. Check that your Redis host and port match the values in `ControlPanelConfig` (default: `localhost:6379`) or the URL passed to `get_redis_memory()`.

**CLAUDE.md file loading**

- Failures in `ClaudeMemoryLoader.load_all_memory()` typically involve missing or unreadable `CLAUDE.md` files. `ClaudeMemoryConfig.validate_files` controls whether files are checked before loading; `max_import_depth` (default: `5`) and `max_file_size_bytes` (default: `1 000 000`) bound the import graph — exceeding either silently truncates or raises depending on the backend.

**Security and permissions**

- `MemoryPermissionError` / `SecurityError` / `ShortTermSecurityError` — raised when a caller attempts an operation that violates the classification or access-tier rules defined in `ClassificationRules`. The pattern's `Classification` level determines which `AccessTier` is required.

## Where errors originate

The following functions are the most common raise sites. Trace a failure back through the call stack to find which one is involved.

| Function | Module | What goes wrong |
|---|---|---|
| `get_railway_redis()` | `memory/__init__.py` | Raises `OSError` when `REDIS_URL` is not set |
| `get_redis_memory()` | `memory/config.py` | Fails if the URL is malformed or the environment is misconfigured |
| `parse_redis_url()` | `memory/config.py` | Raises on an invalid Redis URL format |
| `get_redis_config()` | `memory/config.py` | Returns stale or missing values when legacy environment variables are absent |
| `ClaudeMemoryLoader.load_all_memory()` | `memory/claude_memory.py` | Fails on unreadable files, import cycles, or depth/size limit violations |
| `MemoryControlPanel.health_check()` | `memory/control_panel.py` | Returns a degraded status dict when Redis or storage is unreachable |
| `check_redis_connection()` | `memory/__init__.py` | Returns a status dict indicating connection failure; does not raise |

## How to diagnose

1. **Check the exception type first.** `OSError` points to a missing environment variable or an unreachable host. `MemoryPermissionError` or `SecurityError` points to a classification mismatch. `ValueError` in `parse_redis_url()` points to a malformed connection string.

2. **Verify Redis availability before anything else.** Call `is_redis_available()` — it checks the Redis subsystem without importing it, so it is safe to call early. Then call `check_redis_connection()` for a detailed status dict that includes host, port, and reachability.

3. **Inspect `ControlPanelConfig` and environment variables.** Confirm that `redis_host`, `redis_port`, and `storage_dir` match your deployment. For Railway, confirm that `REDIS_URL` is set; `get_railway_redis()` raises immediately if it is not.

4. **For CLAUDE.md failures, check `ClaudeMemoryConfig`.** Call `ClaudeMemoryLoader.get_loaded_files()` to see which files were successfully loaded before the failure. Check `max_import_depth` (default: `5`) if you have nested imports, and `max_file_size_bytes` (default: `1 000 000`) if you load large files.

5. **For permission errors, check the pattern's classification.** `MemoryPermissionError` means the caller's `AccessTier` does not satisfy the pattern's `Classification`. Review the `ClassificationRules` in use and confirm the agent's credentials grant the required tier.

6. **Run `MemoryControlPanel.health_check()`.** This returns a dict covering Redis status, storage directory access, and audit log availability. A degraded result here usually explains upstream failures in `stash()`, `retrieve()`, or `search()`.

## Source files

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
