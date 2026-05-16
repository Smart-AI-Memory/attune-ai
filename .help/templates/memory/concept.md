---
type: concept
name: memory-concept
feature: memory
depth: concept
generated_at: 2026-05-16T06:14:13.774390+00:00
source_hash: 54f52a79be1ecfe32e99b4f09f84bda845815a0129b603c252aa4c74c2e1a61c
status: generated
---

# Memory

Attune's memory system gives agents a structured way to store, retrieve, and search information across two distinct layers: a fast short-term backend (typically Redis) and a file-based long-term layer built from `CLAUDE.md` files loaded at startup.

## Two memory layers

Understanding the distinction between the two layers helps you choose the right approach for a given task.

**Short-term memory** is backed by `MemoryBackend`, a protocol that any compliant implementation must satisfy. It defines five core operations — `stash`, `retrieve`, `delete`, `keys`, and `is_connected` — plus `get_stats` and `close` for observability and lifecycle management. Short-term entries can carry a TTL and are optionally scoped to a specific `agent_id`, which means multiple agents can share one backend without colliding. When you need semantic search on top of basic key-value access, `SearchableMemoryBackend` extends `MemoryBackend` with a `search` method and a `promote` method that graduates session data into longer-lived storage.

**Long-term memory** is file-based. `ClaudeMemoryLoader` walks a project's directory tree looking for `CLAUDE.md` files at the enterprise, user, and project levels — controlled by the `load_enterprise`, `load_user`, and `load_project` flags on `ClaudeMemoryConfig`. Each discovered file becomes a `MemoryFile` dataclass that records its level (enterprise/user/project), its path, its raw content, any `imports` it declares, and a `load_order` integer that determines merge precedence. `ClaudeMemoryLoader.load_all_memory()` assembles all of these into a single string your agent can consume.

## How the pieces fit together

At runtime, the two layers complement each other:

1. On startup, `ClaudeMemoryLoader` reads `CLAUDE.md` files up to `max_import_depth` levels deep (default 5) and no larger than `max_file_size_bytes` (default 1 MB). The result is a static context string injected into the agent's working memory.
2. During a session, the agent calls `stash` and `retrieve` on a `MemoryBackend` instance — usually `RedisShortTermMemory` — to track transient state such as conversation turns or intermediate results.
3. If the backend implements `SearchableMemoryBackend`, the agent can issue natural-language `search` queries against stored entries, then call `promote` to surface a session's accumulated knowledge into long-term storage.

The `MemoryControlPanel` sits above both layers. It wraps a `ControlPanelConfig` (Redis host, port, storage directory, audit directory) and exposes administrative operations: `start_redis` / `stop_redis`, `get_statistics`, `list_patterns`, `delete_pattern`, `clear_short_term`, and `export_patterns`. A companion HTTP server (`run_api_server`) exposes these operations as an API with optional API-key authentication (`APIKeyAuth`) and per-IP rate limiting (`RateLimiter`).

## Security and classification

Patterns stored in long-term memory carry a `Classification` that the `ClassificationRules` engine assigns automatically. Healthcare (`patient`, `hipaa`, `phi`), financial (`credit card`, `pci dss`), and proprietary (`confidential`, `trade secret`) keywords each map to separate classification tiers. `PIIScrubber` and `SecretsDetector` run before storage to strip personally identifiable information and credentials. `AuditLogger` records every write and delete as an `AuditEvent` so you have a full trail of what changed and when.

## When this matters

You interact with the memory system whenever you need an agent to:

- Remember facts across turns in a session (`stash` / `retrieve` with an `agent_id`)
- Start a session with project-specific context already loaded (`ClaudeMemoryLoader`)
- Search accumulated knowledge semantically rather than by exact key (`SearchableMemoryBackend.search`)
- Operate in a regulated environment where stored patterns must be classified and auditable (`Classification`, `AuditLogger`)
- Deploy on Railway or another hosted environment (`get_railway_redis`, which reads `REDIS_URL` from the environment and raises `OSError` with remediation steps if it is absent)

## Key interfaces at a glance

| Interface | Layer | Purpose |
|---|---|---|
| `MemoryBackend` | Short-term | Protocol every backend must implement |
| `SearchableMemoryBackend` | Short-term | Adds semantic search and promotion to long-term storage |
| `ClaudeMemoryConfig` | Long-term | Controls which `CLAUDE.md` levels load and how deep |
| `MemoryFile` | Long-term | One loaded file with level, path, content, and load order |
| `ClaudeMemoryLoader` | Long-term | Walks the project tree and assembles the context string |
| `MemoryControlPanel` | Admin | Status, statistics, pattern management, Redis lifecycle |
