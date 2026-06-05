---
type: concept
name: memory-concept
feature: memory
depth: concept
generated_at: 2026-06-04T23:45:26.837124+00:00
source_hash: c6803543f79e6bd38c2393239d6731920690afcab986165d0ce938b8ba0d5c25
status: generated
---

# Memory

Attune AI's memory system gives agents a structured way to store, retrieve, and search information across two distinct layers: short-term runtime state backed by Redis, and long-term knowledge loaded from `CLAUDE.md` files on disk.

## Two-layer architecture

The memory system separates concerns between what an agent knows right now and what it should always know.

**Short-term memory** holds transient, agent-scoped data during a session. The `MemoryBackend` protocol defines the interface every short-term backend must satisfy: `stash`, `retrieve`, `delete`, `keys`, and `is_connected`. Any backend can report whether it supports real-time pub/sub (`supports_realtime`) or distributed access across agents (`supports_distributed`). `RedisShortTermMemory` is the production implementation; a mock is available when Redis is absent.

**Semantic search** extends short-term storage. `SearchableMemoryBackend` adds `search`, `remember`, `promote`, `prune`, and `recent` on top of `MemoryBackend`. Use `promote` to graduate session-scoped memories into longer-lived storage, and `prune` to expire entries older than `max_age_days`.

**Long-term memory** comes from `CLAUDE.md` files that `ClaudeMemoryLoader` reads at startup. `ClaudeMemoryConfig` controls which scopes are loaded (`load_enterprise`, `load_user`, `load_project`), how deeply nested `@import` chains are followed (`max_import_depth`, default 5), and whether files are validated before use (`validate_files`). Each loaded file becomes a `MemoryFile` dataclass recording its `level`, `path`, `content`, `imports`, and `load_order`, which determines the priority when content from different scopes conflicts.

## How the pieces fit together

```
ClaudeMemoryConfig
       │
       ▼
ClaudeMemoryLoader.load_all_memory()
       │  reads CLAUDE.md files at enterprise / user / project levels
       ▼
list[MemoryFile]  ──► merged context string injected into agent prompt

Agent runtime
       │
       ▼
MemoryBackend  (stash / retrieve / delete)
       │
SearchableMemoryBackend  (search / remember / promote / prune)
       │
RedisShortTermMemory  ◄── get_redis_memory() or get_railway_redis()
```

`ClaudeMemoryLoader` resolves and flattens the file graph, respecting `max_file_size_bytes` (default 1 MB) to guard against runaway imports. `get_redis_memory()` reads connection parameters from environment variables; `get_railway_redis()` raises `OSError` with actionable guidance if `REDIS_URL` is missing.

## Operational control

`MemoryControlPanel` exposes administrative operations over the running memory layer. You can call `status()` and `health_check()` to inspect liveness, `get_statistics()` for a `MemoryStats` snapshot, and `clear_short_term(agent_id)` to flush a specific agent's data. `list_patterns` and `delete_pattern` manage stored behavioral patterns, and `export_patterns` writes them to a file for backup or audit.

`ControlPanelConfig` sets the Redis coordinates (`redis_host`, `redis_port`), the on-disk storage path (`storage_dir`), and whether Redis is launched automatically (`auto_start_redis`).

`run_api_server` wraps `MemoryControlPanel` in an HTTP API with optional API-key auth (`APIKeyAuth`), per-IP rate limiting (`RateLimiter`, default 100 requests per 60-second window), SSL termination, and CORS origin filtering.

## Security and classification

Patterns stored in long-term memory carry a `Classification` label. `ClassificationRules` match content against domain-specific keyword lists — `HEALTHCARE_KEYWORDS`, `FINANCIAL_KEYWORDS`, and `PROPRIETARY_KEYWORDS` — and route sensitive entries through `EncryptionManager`. `PIIScrubber` and `SecretsDetector` run on content before it is persisted, preventing accidental storage of PII or credentials. `AuditLogger` records every read and write as an `AuditEvent` for compliance review.

## When this matters

- **Multi-agent deployments** — `supports_distributed` tells you whether the active backend can share state across agents without race conditions. `CrossSessionCoordinator` coordinates agents using the `empathy:sessions` pub/sub channel and `empathy:active_agents` key.
- **Project bootstrapping** — `create_default_project_memory(project_root, framework)` writes a starter `.claude/CLAUDE.md` so new projects have a memory scaffold from day one.
- **Environment portability** — `is_redis_available()` lets calling code decide at runtime whether to use Redis or fall back to a mock, without importing the Redis client unconditionally.
