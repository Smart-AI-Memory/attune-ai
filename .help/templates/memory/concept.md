---
type: concept
name: memory-concept
feature: memory
depth: concept
generated_at: 2026-06-12T00:20:52.581029+00:00
source_hash: 439162c85525d4aff627199f05d3f52d259589b86b947c5b2f62b832a0d15fae
status: generated
scaffold_hash: fc0d9984517f8c22ce4ac76cb18edf9fd2a3bcc4d42b5edbc949332d6846906e
---

# Memory

Attune AI memory is a three-layer system that gives agents short-term working storage, searchable long-term pattern recall, and static project context — all with built-in classification, PII scrubbing, and secrets detection before anything reaches persistent storage.

## Memory layers

Each layer serves a different retention horizon and access pattern.

**Short-term agent memory** is a keyed store scoped per `agent_id`, backed by any class that implements the `MemoryBackend` protocol. The core operations are `stash(key, value, ttl, agent_id)`, `retrieve(key, agent_id)`, `delete(key)`, and `keys(pattern)`. An optional `ttl` argument expires entries automatically. Two capability flags determine backend fitness for your deployment: `supports_realtime()` and `supports_distributed()`. A Redis-backed store passes both; an in-process mock typically passes neither. Call `is_connected()` before use and `get_stats()` for runtime metrics.

**Long-term searchable memory** extends `MemoryBackend` through the `SearchableMemoryBackend` protocol. Rather than retrieving by exact key, you query by content: `search(query, limit)` returns ranked results, and `recent(limit)` surfaces the most recently stored entries. Use `remember(content, topics=[...])` to store an entry, `promote(session_id)` to graduate session-scoped memories into the durable store, and `prune(max_age_days)` to expire stale entries.

**Static project context** comes from CLAUDE.md files resolved at enterprise, user, and project levels. `ClaudeMemoryLoader` reads these files in order — controlled by the `load_enterprise`, `load_user`, and `load_project` fields on `ClaudeMemoryConfig` — and returns a single merged string from `load_all_memory()`. Files that import other paths are followed recursively up to `max_import_depth` (default `5`). Set `validate_files=True` to reject any file that exceeds `max_file_size_bytes` (default `1000000` bytes). To bootstrap a new project, `create_default_project_memory(project_root, framework='empathy')` writes a starter `.claude/CLAUDE.md` with the expected structure.

## Security controls

Classification and scrubbing run before any pattern reaches durable storage. `ClassificationRules` assigns a `Classification` level using keyword lists (`HEALTHCARE_KEYWORDS`, `FINANCIAL_KEYWORDS`, `PROPRIETARY_KEYWORDS`) and type lists (`SENSITIVE_PATTERN_TYPES`, `INTERNAL_PATTERN_TYPES`). The `PIIScrubber` strips personally identifiable information, and `SecretsDetector` flags credential-like content. `EncryptionManager` handles at-rest encryption for patterns that require it. `AuditLogger` records every write and access as an `AuditEvent` for compliance trails.

## Enterprise control surface

`MemoryControlPanel` exposes runtime operations without requiring code changes. You can check `status()` and `health_check()`, browse stored patterns with `list_patterns(classification=None, limit=100)`, remove a specific pattern with `delete_pattern(pattern_id, user_id)`, bulk-clear short-term entries with `clear_short_term(agent_id)`, and export pattern sets to disk with `export_patterns(output_path)`.

The panel is configured through `ControlPanelConfig`, which defaults Redis to `localhost:6379` and uses `./memdocs_storage` for pattern documents. When `auto_start_redis=True`, the panel starts Redis automatically if it isn't already running.

`run_api_server(panel, host, port)` wraps the panel in an HTTP server backed by `MemoryAPIHandler`, which handles `GET`, `POST`, `DELETE`, and `OPTIONS` requests. Optional arguments let you add TLS (`ssl_certfile`, `ssl_keyfile`), restrict access with `APIKeyAuth` (via `api_key`), and enforce request budgets with `RateLimiter` (`rate_limit_requests`, `rate_limit_window`). Set `allowed_origins` for CORS control.

For Railway deployments, `get_railway_redis()` reads `REDIS_URL` from the environment and raises `OSError` with setup instructions if the variable is absent.

## Integration surface

| Type | Name | Role |
|------|------|------|
| Protocol | `MemoryBackend` | Short-term key-value store with TTL and agent scoping |
| Protocol | `SearchableMemoryBackend` | Extends `MemoryBackend` with semantic search, promotion, and pruning |
| Dataclass | `ClaudeMemoryConfig` | Controls which CLAUDE.md levels load, import depth, and file-size limits |
| Dataclass | `MemoryFile` | One resolved CLAUDE.md file: `level`, `path`, `content`, `imports`, `load_order` |
| Class | `ClaudeMemoryLoader` | Resolves and merges CLAUDE.md files; primary entry point is `load_all_memory()` |
| Class | `MemoryControlPanel` | Runtime management for patterns, short-term entries, and Redis lifecycle |
| Dataclass | `ControlPanelConfig` | Redis coordinates (`redis_host`, `redis_port`) and storage paths for the control panel |
| Function | `is_redis_available()` | Lightweight probe that checks Redis availability without importing the subsystem |
| Function | `get_redis_memory(url, use_mock)` | Factory that reads environment config and returns a `RedisShortTermMemory` instance |
| Function | `get_railway_redis()` | Railway-specific factory; raises `OSError` if `REDIS_URL` is absent |
| Function | `create_default_project_memory(project_root, framework)` | Writes a starter CLAUDE.md to bootstrap a new project |
