---
type: troubleshooting
name: memory-troubleshooting
feature: memory
depth: troubleshooting
generated_at: 2026-05-16T06:14:13.797051+00:00
source_hash: 54f52a79be1ecfe32e99b4f09f84bda845815a0129b603c252aa4c74c2e1a61c
status: generated
---

# Troubleshoot memory

## Before you start

The memory subsystem handles short-term storage (Redis-backed), long-term pattern storage (MemDocs), and Claude memory file loading (CLAUDE.md). Symptoms often fall into one of three areas: Redis connectivity, memory file loading, or classification and security access.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `OSError: REDIS_URL not found` | Run `is_redis_available()` before calling `get_railway_redis()`. Confirm `REDIS_URL` is set in your environment, or add Redis to your Railway project with `railway add --database redis`. |
| `stash()` or `retrieve()` returns `None` unexpectedly | Call `backend.is_connected()` to confirm the backend is live. Then call `backend.get_stats()` to check key counts and TTL state. |
| CLAUDE.md memory files are not loaded | Check `ClaudeMemoryConfig.enabled` — it defaults to `False`. Confirm `project_root` resolves to the directory containing `.claude/CLAUDE.md`. Call `loader.get_loaded_files()` to see what was actually imported. |
| Memory files load but content is missing or truncated | Check `ClaudeMemoryConfig.max_file_size_bytes` (default: 1,000,000 bytes) and `max_import_depth` (default: 5). Files exceeding the size limit or beyond the import depth are silently skipped when `validate_files=True`. |
| `MemoryPermissionError` or `SecurityError` on pattern access | Call `check_access()` with the pattern's classification. Confirm the agent's credentials cover the required `Classification` level (e.g., `HEALTHCARE`, `FINANCIAL`, `PROPRIETARY`). |
| Redis starts but the control panel reports unhealthy | Call `panel.health_check()` and inspect the returned dict. Then call `panel.status()` to see whether `auto_start_redis` succeeded. |
| Intermittent failures across agents or sessions | Check for stale state under the `empathy:active_agents` and `empathy:service_lock` Redis keys. Call `panel.clear_short_term(agent_id=...)` to flush a specific agent's short-term memory. |

## Diagnosis steps

Work through these in order — each step is cheaper than the one that follows it.

1. **Confirm Redis availability.**
   Before investigating application logic, verify the Redis subsystem is reachable:

   ```python
   from attune.memory import is_redis_available
   print(is_redis_available())
   ```

   If this returns `False`, fix connectivity before continuing. For Railway deployments, ensure `REDIS_URL` is set; for local deployments, confirm Redis is running on `localhost:6379` (the default `ControlPanelConfig` values).

2. **Check the connection status explicitly.**
   If Redis appears available but behavior is wrong, get a detailed status report:

   ```python
   from attune.memory import check_redis_connection
   print(check_redis_connection())
   ```

   This returns a dict with connection state you can inspect without modifying any code.

3. **Inspect what memory files were loaded.**
   If CLAUDE.md content is missing, call `get_loaded_files()` after `load_all_memory()` to see the exact file list:

   ```python
   from attune.memory.claude_memory import ClaudeMemoryLoader, ClaudeMemoryConfig

   config = ClaudeMemoryConfig(enabled=True, project_root="/your/project")
   loader = ClaudeMemoryLoader(config)
   content = loader.load_all_memory()
   print(loader.get_loaded_files())
   ```

   Cross-reference the output against your `max_import_depth` and `max_file_size_bytes` settings.

4. **Run the memory test suite.**
   Before modifying any code, confirm which paths are already covered:

   ```
   pytest -k "memory" -v
   ```

   A failing test that exercises your symptom gives you a reproducible baseline and a fixture you can reuse.

5. **Enable DEBUG logging.**
   If the above steps don't isolate the problem, increase log verbosity and re-run:

   ```python
   import logging
   logging.getLogger("attune.memory").setLevel(logging.DEBUG)
   ```

   Look for unexpected early returns, TTL expirations, or classification rejections in the output.

6. **Pull a full health and statistics report.**
   For control-panel issues, call both `health_check()` and `get_statistics()` together:

   ```python
   panel = MemoryControlPanel()
   print(panel.health_check())
   print(panel.get_statistics())
   ```

   The statistics report exposes pattern counts, storage usage, and audit log state that are not visible in the basic status output.

## Common fixes

- **Redis not found on Railway.** Set the `REDIS_URL` environment variable or run `railway add --database redis`. For external access use `REDIS_PUBLIC_URL`. This is a deployment environment change, not a code change.

- **Claude memory loading is silently disabled.** `ClaudeMemoryConfig.enabled` defaults to `False`. Explicitly set it to `True` when constructing the config, or pass a config with `enabled=True` to `ClaudeMemoryLoader`.

- **Files skipped due to size or depth limits.** Increase `max_file_size_bytes` or `max_import_depth` in `ClaudeMemoryConfig`. Alternatively, restructure deep import chains so critical content appears within the first five levels.

- **Missing default CLAUDE.md.** If no memory file exists for a project, create one with:

  ```python
  from attune.memory.claude_memory import create_default_project_memory
  create_default_project_memory(project_root="/your/project", framework="empathy")
  ```

- **Stale short-term memory causing incorrect agent behavior.** Clear a specific agent's short-term store:

  ```python
  panel = MemoryControlPanel()
  cleared = panel.clear_short_term(agent_id="your-agent-id")
  print(f"Cleared {cleared} entries")
  ```

- **Classification access denied.** Pattern access is gated by `Classification` level. If you see `MemoryPermissionError`, confirm the agent's credentials include the required tier before calling `retrieve()` or `search()`. This may require changes to how agent credentials are provisioned, outside the memory module itself.

- **Redis URL parse failure.** If `get_redis_memory()` raises on an unexpected URL format, test the URL directly:

  ```python
  from attune.memory.config import parse_redis_url
  print(parse_redis_url("redis://your-host:6379"))
  ```

  This isolates whether the problem is in the URL string or in the broader connection setup.

## Source files

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
