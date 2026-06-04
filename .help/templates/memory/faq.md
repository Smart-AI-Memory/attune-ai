---
type: faq
name: memory-faq
feature: memory
depth: faq
generated_at: 2026-06-04T23:45:26.864548+00:00
source_hash: c6803543f79e6bd38c2393239d6731920690afcab986165d0ce938b8ba0d5c25
status: generated
---

# Memory FAQ

## What does the memory feature do?

It provides a backend protocol for storing, retrieving, and searching agent memory — covering short-term key/value storage, semantic search, Claude Code memory file loading, and an enterprise control panel with Redis support.

## When should I use the memory feature?

Use it when your agent or application needs to persist data between steps, search past interactions, load project-level `CLAUDE.md` context files, or manage memory patterns through a control panel. If you only need to check whether Redis is available before importing it, call `is_redis_available()` first.

## What are the main entry points?

It depends on what you want to do:

- **Store and retrieve data** — implement or use `MemoryBackend` (protocol defined in `src/attune/memory/backend.py`), which provides `stash()`, `retrieve()`, `delete()`, and `keys()`.
- **Semantic search** — use `SearchableMemoryBackend`, which extends `MemoryBackend` with `search()`, `remember()`, `promote()`, `prune()`, and `recent()`.
- **Load Claude Code memory files** — use `ClaudeMemoryLoader`, configured with `ClaudeMemoryConfig`, and call `load_all_memory()`.
- **Connect to Redis** — call `get_redis_memory()` for environment-based configuration, or `get_railway_redis()` for Railway deployments.
- **Enterprise control panel** — instantiate `MemoryControlPanel` (configured with `ControlPanelConfig`) and call `status()`, `get_statistics()`, or `health_check()`.

## Does the memory feature require Redis?

No. Redis is optional. Call `is_redis_available()` to check at runtime without triggering an import error. If Redis is unavailable, you can pass `use_mock=True` to `get_redis_memory()` to get a mock backend instead.

## What happens if I call `get_railway_redis()` and there is no `REDIS_URL`?

It raises an `OSError` with a message telling you to add Redis to your Railway project and run `railway add --database redis`. For external access, the error message points you to `REDIS_PUBLIC_URL`.

## How do I load `CLAUDE.md` memory files into my project?

Create a `ClaudeMemoryConfig` (setting `enabled=True` and optionally `project_root`), pass it to `ClaudeMemoryLoader`, then call `load_all_memory()`. The loader walks up to `max_import_depth` levels (default `5`) and skips files larger than `max_file_size_bytes` (default `1000000`). Call `get_loaded_files()` to inspect what was loaded, or `clear_cache()` to reset.

## How do I create a default `CLAUDE.md` for a new project?

Call `create_default_project_memory(project_root, framework)`. It writes a `.claude/CLAUDE.md` file in the directory you specify. The `framework` parameter defaults to `'empathy'`.

## How do I parse a Redis URL into connection parameters?

Call `parse_redis_url(url)`. It returns a dict of connection parameters you can pass directly to your Redis client.

## How do I debug memory issues?

Run `pytest -k "memory" -v` first. If the tests pass but your code still fails:

1. Call `check_redis_connection()` to get a status dict for the Redis connection.
2. Call `MemoryControlPanel.health_check()` if you are using the control panel.
3. Check `MemoryBackend.is_connected()` and `MemoryBackend.get_stats()` on your backend instance.
4. Add a `logger.debug` statement at the failure point and re-run with logging enabled.

For symptom-based diagnosis, see the troubleshooting page for this feature.

## Where are the source files?

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
