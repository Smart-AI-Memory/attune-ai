---
type: note
name: memory-note
feature: memory
depth: note
generated_at: 2026-05-16T06:14:13.805912+00:00
source_hash: 54f52a79be1ecfe32e99b4f09f84bda845815a0129b603c252aa4c74c2e1a61c
status: generated
---

# Note: memory

## Context

The `memory` feature covers short-term storage, semantic search, Claude Code memory file loading, Redis configuration, and enterprise memory management. Its source lives under `src/attune/memory/`.

## Public surface

The package exposes two layers at its boundary: protocols (abstract classes) and factory functions.

**Protocols** (`src/attune/memory/backend.py`):

- `MemoryBackend` — the base protocol every short-term memory backend must implement. Key methods: `stash`, `retrieve`, `delete`, `keys`, `is_connected`, `get_stats`, `close`, `supports_realtime`, and `supports_distributed`.
- `SearchableMemoryBackend` — extends `MemoryBackend` with `search` (semantic query) and `promote` (elevate a session's patterns to long-term storage).

**Claude Code memory** (`src/attune/memory/claude_memory.py`):

- `ClaudeMemoryConfig` — dataclass controlling which memory levels (`enterprise`, `user`, `project`) are loaded, file size limits, import depth, and validation. Defaults to `enabled: False`.
- `MemoryFile` — dataclass representing a single loaded `CLAUDE.md` file, including its level, path, content, import list, and load order.
- `ClaudeMemoryLoader` — loads and caches the full `CLAUDE.md` hierarchy for a project. Call `load_all_memory()` to get the merged content string; call `clear_cache()` to force a reload.

**Factory functions**:

| Function | Module | Purpose |
|---|---|---|
| `is_redis_available()` | `__init__.py` | Checks Redis availability without importing the subsystem |
| `create_default_project_memory()` | `claude_memory.py` | Writes a starter `.claude/CLAUDE.md` for a project |
| `parse_redis_url()` | `config.py` | Parses a Redis URL string into connection parameters |
| `get_redis_config()` | `config.py` | Reads Redis config from environment variables (legacy dict API) |
| `get_redis_memory()` | `config.py` | Returns a configured `RedisShortTermMemory` instance |

## Composition pattern

The protocols and functions are designed to work together: factory functions like `get_redis_memory()` return objects that implement `MemoryBackend`, and `ClaudeMemoryLoader` accepts a `ClaudeMemoryConfig` instance to control its behavior. Code that consumes the memory package typically constructs a backend via a factory function, then passes it to higher-level components such as `UnifiedMemory` or `MemoryControlPanel`.

## Version and deprecation

The package is at version `2.2.0` (`__version__`). The Redis configuration module (`src/attune/memory/config.py`) is marked deprecated in favor of direct environment-based configuration via `get_redis_memory()`.
