---
type: note
name: memory-note
feature: memory
depth: note
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 7d6a88f7e825fe56e3b06e3bce6dd904fe6a75cd1c13a3a134e4b44138df245e
status: generated
---

# Note: memory

## Context

The memory subsystem (`src/attune/memory/`) covers short-term storage, semantic search, Claude Code memory file loading, Redis configuration, and an enterprise control panel. It is versioned at `2.2.0`.

## Two-layer public surface

The package exposes two protocol classes that define the storage contract and a set of top-level functions that configure and instantiate backends.

**Protocols** (defined in `src/attune/memory/backend.py`):

- `MemoryBackend` — the base protocol for short-term memory backends. Every backend must implement `stash`, `retrieve`, `delete`, `keys`, `is_connected`, `get_stats`, `close`, `supports_realtime`, and `supports_distributed`.
- `SearchableMemoryBackend` — extends `MemoryBackend` with semantic operations: `search`, `remember`, `promote`, `prune`, and `recent`.

**Configuration and factory functions** (in `src/attune/memory/config.py` and `src/attune/memory/__init__.py`):

- `is_redis_available()` — probes Redis availability without importing the Redis subsystem, making it safe to call at startup.
- `parse_redis_url(url)` — converts a Redis URL string into a connection-parameter dict.
- `get_redis_config()` — reads connection parameters from environment variables; marked legacy because it returns a plain dict rather than a typed config object.
- `get_redis_memory(url, use_mock)` — the preferred factory; returns a `RedisShortTermMemory` instance configured from the environment.

The functions and classes are designed to compose: factory functions typically return objects that satisfy `MemoryBackend` or `SearchableMemoryBackend`, and backend methods mirror the top-level function signatures.

## Claude Code memory integration

`ClaudeMemoryLoader` (in `src/attune/memory/claude_memory.py`) loads and caches `CLAUDE.md` files. Its behavior is controlled by `ClaudeMemoryConfig`, which lets you enable or disable each memory scope (`load_enterprise`, `load_user`, `load_project`), cap file size with `max_file_size_bytes` (default 1 000 000 bytes), and limit import recursion with `max_import_depth` (default 5). Each loaded file is represented as a `MemoryFile` dataclass carrying its `level`, `path`, `content`, `imports`, and `load_order`.

`create_default_project_memory(project_root, framework)` writes a starter `.claude/CLAUDE.md` file into a project tree. The injected block is delimited by the markers `<!-- attune-lessons-start -->` and `<!-- attune-lessons-end -->`.

## Enterprise control panel

`MemoryControlPanel` (configured via `ControlPanelConfig`) provides operational management: starting and stopping Redis, retrieving statistics via `get_statistics()`, listing or deleting stored patterns, clearing short-term memory with `clear_short_term()`, and exporting patterns with `export_patterns()`. `run_api_server()` exposes these operations over HTTP with optional API-key authentication (`APIKeyAuth`), rate limiting (`RateLimiter`), and TLS.

## Railway deployment

`get_railway_redis()` is a convenience factory for Railway-hosted deployments. It raises `OSError` if `REDIS_URL` is not set in the environment, with a message directing you to run `railway add --database redis`.
