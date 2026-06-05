---
type: troubleshooting
name: memory-troubleshooting
feature: memory
depth: troubleshooting
generated_at: 2026-06-04T23:45:26.861810+00:00
source_hash: c6803543f79e6bd38c2393239d6731920690afcab986165d0ce938b8ba0d5c25
status: generated
---

# Troubleshoot memory

## Before you start

The memory subsystem handles short-term storage (backed by Redis), long-term pattern storage, and Claude Code memory file loading (`CLAUDE.md`). Symptoms often fall into one of three areas: Redis connectivity, memory file loading, or security/classification errors.

## Symptom table

| If you observe | Check |
|---|---|
| `OSError: REDIS_URL not found` | The `REDIS_URL` environment variable is unset. On Railway, run `railway add --database redis`. For external access, use `REDIS_PUBLIC_URL`. |
| `is_redis_available()` returns `False` | Call `check_redis_connection()` to get a detailed status dict, then verify Redis is reachable at the configured host and port. |
| `stash()` or `retrieve()` returns `None` unexpectedly | Confirm `is_connected()` returns `True` on your `MemoryBackend` instance. A `False` result means the backend silently dropped the operation. |
| `load_all_memory()` returns empty or partial content | Check `get_loaded_files()` on your `ClaudeMemoryLoader` instance to see which `CLAUDE.md` files were found. Verify `ClaudeMemoryConfig.enabled` is `True` and that `project_root` points to the correct directory. |
| Memory file imports not resolving | `ClaudeMemoryConfig.max_import_depth` defaults to `5`. A deeply nested import chain beyond this limit is silently truncated. |
| Large memory files silently skipped | `ClaudeMemoryConfig.max_file_size_bytes` defaults to `1000000` (1 MB). Files exceeding this limit are not loaded. |
| `MemoryControlPanel.status()` reports Redis stopped | Call `panel.start_redis(verbose=True)` to attempt a restart and read the returned `RedisStatus` for the failure reason. |
| `SecurityError` or `MemoryPermissionError` on pattern access | The pattern's `Classification` level exceeds your agent's `AccessTier`. Check the pattern's classification with `list_patterns()` and confirm the calling agent's credentials. |
| Intermittent key misses under load | The `RateLimiter` may be dropping requests. Call `get_remaining(client_ip)` to check remaining quota for the client IP. The default window is 60 seconds / 100 requests. |
| `get_railway_redis()` raises `OSError` | `REDIS_URL` is not set in the Railway environment. Add Redis to your project (`railway add --database redis`) or set `REDIS_PUBLIC_URL` for external access. |

## Diagnosis steps

Follow these steps in order — each one is cheaper than the next.

### 1. Check Redis availability

Before investigating application code, confirm Redis itself is reachable:

```python
from attune.memory import check_redis_connection

status = check_redis_connection()
print(status)
```

If the status dict shows a connection failure, fix the Redis issue before continuing. Use `is_redis_available()` for a quick boolean check when you don't need details.

### 2. Inspect your environment variables

`get_redis_config()` reads connection parameters from environment variables. Confirm the expected variables are set:

```bash
echo $REDIS_URL
```

If you use `parse_redis_url()` directly, verify the URL string is well-formed (e.g., `redis://localhost:6379/0`).

### 3. Verify backend connectivity in code

Instantiate your backend and call `is_connected()` before performing any operations:

```python
backend = get_redis_memory()  # or get_railway_redis() on Railway
print(backend.is_connected())
print(backend.get_stats())
```

A `False` result from `is_connected()` means all subsequent `stash()` and `retrieve()` calls will fail silently.

### 4. Check Claude memory file loading

If `load_all_memory()` returns less content than expected, inspect which files were actually loaded:

```python
from attune.memory.claude_memory import ClaudeMemoryLoader, ClaudeMemoryConfig

config = ClaudeMemoryConfig(enabled=True, project_root="/path/to/project")
loader = ClaudeMemoryLoader(config)
loader.load_all_memory()
print(loader.get_loaded_files())
```

Cross-check the output against your `CLAUDE.md` file locations and the `max_import_depth` / `max_file_size_bytes` limits in `ClaudeMemoryConfig`.

### 5. Query control panel health

If you are running `MemoryControlPanel`, call `health_check()` for a unified status report:

```python
from attune.memory.control_panel import MemoryControlPanel

panel = MemoryControlPanel()
print(panel.health_check())
print(panel.status())
```

Use `get_statistics()` to identify abnormal counts (e.g., unexpectedly high or zero pattern counts).

### 6. Run the related tests

```bash
pytest -k "memory" -v
```

A failing test that exercises the same path as your bug will also give you a fixture you can reuse to isolate the issue.

## Common fixes

**Redis not running — start it via the control panel:**

```python
panel = MemoryControlPanel()
result = panel.start_redis(verbose=True)
print(result)  # RedisStatus with reason if startup failed
```

If `ControlPanelConfig.auto_start_redis` is `False`, Redis will not start automatically. Set it to `True` or start Redis manually before initializing the panel.

**Missing `REDIS_URL` on Railway:**

```bash
railway add --database redis
```

For external access, set `REDIS_PUBLIC_URL` instead and pass it explicitly to `get_redis_memory(url=...)`.

**Memory files not loading — create a default file:**

```python
from attune.memory.claude_memory import create_default_project_memory

create_default_project_memory("/path/to/project", framework="empathy")
```

This creates `.claude/CLAUDE.md` under the given project root.

**Stale short-term memory causing unexpected hits:**

```python
panel = MemoryControlPanel()
cleared = panel.clear_short_term(agent_id="your-agent-id")
print(f"Cleared {cleared} entries")
```

**Import depth or file size limits blocking content:**
Increase the limits in `ClaudeMemoryConfig` when constructing `ClaudeMemoryLoader`:

```python
config = ClaudeMemoryConfig(
    enabled=True,
    max_import_depth=10,        # default is 5
    max_file_size_bytes=5000000  # default is 1000000
)
```

**Dependency version mismatch:**
The Redis backend behavior depends on the installed Redis client library. Run `pip show redis` to confirm the version matches what your environment expects, then reinstall if needed.

## Source files

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
