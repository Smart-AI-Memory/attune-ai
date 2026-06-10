---
type: troubleshooting
name: memory-troubleshooting
feature: memory
depth: troubleshooting
generated_at: 2026-06-10T07:07:04.792122+00:00
source_hash: 570dd4977cd655a0cf44a47b917577fd70f4cf08eb5d256d4da2915dbea871f0
status: generated
---

# Troubleshoot memory

## Before you start

The memory subsystem covers three concerns: short-term storage via `MemoryBackend` and `SearchableMemoryBackend`, Claude Code memory file loading via `ClaudeMemoryLoader`, and enterprise control panel operations via `MemoryControlPanel`. Identify which layer is failing before you dig in — Redis connectivity issues look different from CLAUDE.md import failures or pattern classification errors.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `stash()` or `retrieve()` returns `None` or `False` unexpectedly | Call `is_connected()` on your backend instance; if it returns `False`, Redis is not reachable |
| `get_railway_redis()` raises `OSError: REDIS_URL not found` | Confirm the `REDIS_URL` environment variable is set; on Railway, run `railway add --database redis` |
| `ClaudeMemoryLoader.load_all_memory()` returns empty or partial content | Call `get_loaded_files()` to see which CLAUDE.md files were found; check `ClaudeMemoryConfig.max_import_depth` (default `5`) and `max_file_size_bytes` (default `1000000`) |
| `MemoryControlPanel.health_check()` reports unhealthy | Check `status()` first — it shows Redis connectivity and storage directory state separately |
| `search()` or `remember()` fails on a backend | Confirm your backend implements `SearchableMemoryBackend`, not just `MemoryBackend`; the base protocol does not expose those methods |
| Intermittent `stash()`/`retrieve()` failures under load | Check `RateLimiter.get_remaining()` for the client IP; the default window is 100 requests per 60 seconds |
| Pattern classification returns unexpected results | Verify content does not contain keywords from `HEALTHCARE_KEYWORDS`, `FINANCIAL_KEYWORDS`, or `PROPRIETARY_KEYWORDS` — matches elevate the classification automatically |

## Diagnosis steps

Work through these in order — each step is cheaper than the one that follows.

1. **Check Redis availability without importing it.**
   Call `is_redis_available()` first. If it returns `False`, no backend that depends on Redis will work, and you can skip deeper investigation until connectivity is restored.

   ```python
   from attune.memory import is_redis_available
   print(is_redis_available())
   ```

2. **Inspect the Redis connection details.**
   Call `check_redis_connection()` for a structured status dict that includes the host, port, and any error message. If you are parsing a `REDIS_URL`, call `parse_redis_url(url)` to confirm it resolves to the expected host and port before passing it to `get_redis_memory()`.

   ```python
   from attune.memory import check_redis_connection
   print(check_redis_connection())
   ```

3. **Verify backend connectivity and stats.**
   On a live backend instance, call `is_connected()` and `get_stats()`. A backend can pass `is_redis_available()` but still fail `is_connected()` if credentials or the specific DB index are wrong.

4. **Check which memory files were loaded.**
   If the issue is in Claude memory loading, call `get_loaded_files()` on your `ClaudeMemoryLoader` instance. Cross-check the returned paths against the `project_root` in `ClaudeMemoryConfig`. If `validate_files` is `True` (the default), files that fail validation are silently skipped.

   ```python
   loader = ClaudeMemoryLoader()
   loader.load_all_memory(project_root="/your/project")
   print(loader.get_loaded_files())
   ```

5. **Run the control panel health check.**
   For enterprise control panel issues, call `MemoryControlPanel.health_check()`, then `status()` for a breakdown. If Redis isn't running and `ControlPanelConfig.auto_start_redis` is `True`, call `start_redis(verbose=True)` and check the returned `RedisStatus`.

6. **Run targeted tests.**
   ```
   pytest -k "memory" -v
   ```
   If a test covers your failing path, its fixtures give you a minimal reproduction environment.

## Common fixes

**Redis not reachable**
Set `REDIS_URL` in your environment, or confirm the host and port in `ControlPanelConfig` (defaults: `redis_host='localhost'`, `redis_port=6379`). For Railway deployments, the variable must be `REDIS_URL`; `REDIS_PUBLIC_URL` is for external access only.

```bash
export REDIS_URL=redis://localhost:6379
```

**`load_all_memory()` returns less content than expected**
Increase `max_import_depth` in `ClaudeMemoryConfig` if your project has deeply nested CLAUDE.md imports. Increase `max_file_size_bytes` if large files are being skipped. Set `validate_files=False` temporarily to confirm that validation is the cause — then fix the offending files rather than leaving validation off.

```python
config = ClaudeMemoryConfig(max_import_depth=10, max_file_size_bytes=5_000_000)
loader = ClaudeMemoryLoader(config)
```

**No CLAUDE.md exists for a new project**
Call `create_default_project_memory()` to generate a `.claude/CLAUDE.md` scaffold:

```python
from attune.memory.claude_memory import create_default_project_memory
create_default_project_memory(project_root="/your/project", framework="empathy")
```

**`search()` or `remember()` raises `AttributeError`**
Your backend only implements `MemoryBackend`. To use semantic search, promote it to `SearchableMemoryBackend`. This is a protocol change — you need a backend class that implements `search()`, `remember()`, `promote()`, `prune()`, and `recent()`.

**Stale short-term memory causing wrong results**
Clear short-term memory for the affected agent:

```python
panel = MemoryControlPanel()
cleared = panel.clear_short_term(agent_id="your-agent-id")
print(f"Cleared {cleared} entries")
```

To reset the loader's file cache between runs:

```python
loader.clear_cache()
```

**Version mismatch after a dependency upgrade**
Run `pip show attune` to confirm the installed version. The module exposes `__version__ = '2.2.0'` — check that your code's expectations match this version before filing a bug.

## Source files

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
