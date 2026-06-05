---
type: note
name: memory-note
feature: memory
depth: note
generated_at: 2026-06-04T23:45:26.872218+00:00
source_hash: c6803543f79e6bd38c2393239d6731920690afcab986165d0ce938b8ba0d5c25
status: generated
---

# Note: memory

The memory subsystem covers three concerns: short-term storage, semantic search, and Claude Code memory file (`CLAUDE.md`) loading. Its public surface lives under `src/attune/memory/`.

## Two backend protocols

`MemoryBackend` is the base protocol for any short-term memory backend. It defines the core operations — `stash`, `retrieve`, `delete`, `keys`, `is_connected`, `get_stats`, `close`, `supports_realtime`, and `supports_distributed`.

`SearchableMemoryBackend` extends `MemoryBackend` with semantic capabilities: `search`, `remember`, `promote`, `prune`, and `recent`. A backend that implements `SearchableMemoryBackend` can answer natural-language queries in addition to exact-key lookups.

## Claude memory file loading

`ClaudeMemoryLoader` reads and caches `CLAUDE.md` files from up to three scopes — enterprise, user, and project — controlled by the `ClaudeMemoryConfig` dataclass fields `load_enterprise`, `load_user`, and `load_project`. Each loaded file is represented as a `MemoryFile` with a `level`, `path`, `content`, `imports` list, and `load_order`.

`max_import_depth` (default `5`) and `max_file_size_bytes` (default `1 000 000`) in `ClaudeMemoryConfig` bound how deeply the loader follows `@import` chains and how large a single file may be.

## Top-level convenience functions

Several module-level functions wrap common setup steps so callers do not have to instantiate classes directly:

| Function | Where | What it does |
|---|---|---|
| `is_redis_available()` | `__init__.py` | Checks Redis availability without importing the Redis subsystem |
| `get_redis_config()` | `config.py` | Reads Redis connection parameters from environment variables (legacy dict API) |
| `parse_redis_url()` | `config.py` | Parses a Redis URL string into a connection-parameter dict |
| `get_redis_memory()` | `config.py` | Creates a `RedisShortTermMemory` instance from environment-based config |
| `create_default_project_memory()` | `claude_memory.py` | Writes a starter `.claude/CLAUDE.md` for a project |

## Control panel and API server

`MemoryControlPanel` (configured via `ControlPanelConfig`) provides an enterprise management layer: Redis lifecycle (`start_redis`, `stop_redis`), pattern management (`list_patterns`, `delete_pattern`, `export_patterns`), short-term memory clearing (`clear_short_term`), and health reporting (`health_check`, `get_statistics`).

`run_api_server` wraps `MemoryControlPanel` in an HTTP server with optional API-key authentication (`APIKeyAuth`), per-IP rate limiting (`RateLimiter`), and SSL.

**Tags:** `memory`, `storage`
