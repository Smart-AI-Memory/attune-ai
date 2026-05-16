---
type: faq
name: memory-faq
feature: memory
depth: faq
generated_at: 2026-05-16T06:14:13.799343+00:00
source_hash: 54f52a79be1ecfe32e99b4f09f84bda845815a0129b603c252aa4c74c2e1a61c
status: generated
---

# Memory FAQ

## What does the memory module do?

It provides storage, lookup, and security for short-term and long-term agent memory. The module defines backend protocols (`MemoryBackend`, `SearchableMemoryBackend`), loads `CLAUDE.md` memory files via `ClaudeMemoryLoader`, and exposes an enterprise control panel (`MemoryControlPanel`) for managing patterns, statistics, and Redis lifecycle.

## When should I use this module?

Use it when your code needs to stash or retrieve keyed values across agent sessions, load project-level memory from `CLAUDE.md` files, or manage memory patterns with access classification and audit logging. If you only need simple in-process state, you don't need this module.

## What are the key entry points?

| Function or class | Where it lives | What it does |
|---|---|---|
| `is_redis_available()` | `memory/__init__.py` | Checks whether Redis is available without importing it — safe to call at startup |
| `get_redis_memory()` | `memory/__init__.py` | Creates a `RedisShortTermMemory` instance using environment-based config |
| `get_railway_redis()` | `memory/__init__.py` | Creates a Redis instance pre-configured for Railway deployments |
| `ClaudeMemoryLoader.load_all_memory()` | `memory/claude_memory.py` | Loads and merges all `CLAUDE.md` files for a project |
| `create_default_project_memory()` | `memory/claude_memory.py` | Scaffolds a default `.claude/CLAUDE.md` for a new project |
| `MemoryControlPanel` | `memory/control_panel.py` | Enterprise panel for status, stats, pattern management, and Redis control |

Start with `is_redis_available()` if you're not sure whether your environment has Redis — it's safe to call without side effects.

## What's the difference between `MemoryBackend` and `SearchableMemoryBackend`?

`MemoryBackend` is the base protocol: stash, retrieve, delete, list keys, check connection, and get stats. `SearchableMemoryBackend` extends it with `search()` for semantic queries and `promote()` to move session memory into longer-term storage. Use `SearchableMemoryBackend` when your backend needs to answer fuzzy or semantic queries, not just exact key lookups.

## How do I check whether Redis is running?

Call `check_redis_connection()` — it returns a status dict without raising an exception. You can also call `is_redis_available()` for a simple boolean check that avoids importing the Redis subsystem entirely.

## What happens if Redis isn't available?

`get_redis_memory()` accepts a `use_mock` parameter. When you set it to `True`, you get a mock backend instead of a live Redis connection, which is useful for testing. `get_railway_redis()` raises `OSError` with a message telling you to add Redis to your Railway project if `REDIS_URL` is not set.

## How do I configure Claude memory file loading?

Pass a `ClaudeMemoryConfig` to `ClaudeMemoryLoader`. The key fields are:

- `enabled` — must be `True` to load any files (defaults to `False`)
- `load_enterprise`, `load_user`, `load_project` — control which memory levels are loaded
- `max_import_depth` — limits recursive `CLAUDE.md` imports (default `5`)
- `max_file_size_bytes` — skips files larger than this (default `1 000 000` bytes)
- `validate_files` — toggles file validation before loading

## How do I debug memory issues?

1. Call `is_redis_available()` or `check_redis_connection()` to confirm the backend is reachable.
2. Run `pytest -k "memory" -v` to check whether the problem is in your code or the module itself.
3. Call `MemoryControlPanel.health_check()` for a structured report of subsystem status.
4. If a specific key is missing, use `MemoryBackend.keys(pattern)` to inspect what's actually stored.
5. Add `logger.debug` at the point where `stash()` or `retrieve()` is called and re-run with logging enabled.

## Where is the source code?

All memory source files are under `src/attune/memory/`.

**Tags:** `memory`, `storage`
