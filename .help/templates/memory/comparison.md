---
type: comparison
name: memory-comparison
feature: memory
depth: comparison
generated_at: 2026-06-04T23:45:26.874785+00:00
source_hash: c6803543f79e6bd38c2393239d6731920690afcab986165d0ce938b8ba0d5c25
status: generated
---

# Comparison: Memory backends and storage strategies

## Context

The memory subsystem provides three distinct storage and retrieval strategies: Redis-backed short-term memory (`RedisShortTermMemory`), file-based Claude memory loaded from `CLAUDE.md` files (`ClaudeMemoryLoader`), and enterprise long-term pattern storage (`MemDocsStorage`). Choosing the wrong one for your use case means either over-engineering a simple need or hitting a hard ceiling when your requirements grow.

## Feature comparison

| Capability | Redis short-term (`RedisShortTermMemory`) | Claude file memory (`ClaudeMemoryLoader`) | Enterprise pattern storage (`MemDocsStorage`) |
|---|---|---|---|
| **Primary protocol** | `MemoryBackend` | — (file-based loader) | `SearchableMemoryBackend` |
| **Semantic search** | No | No | Yes — via `search(query, limit, **filters)` |
| **Real-time support** | Yes — `supports_realtime()` returns `True` | No | Depends on backend |
| **Distributed support** | Yes — `supports_distributed()` returns `True` | No | Yes |
| **TTL / expiry** | Yes — `stash(key, value, ttl=...)` accepts per-key TTL | No — files persist until edited | Yes — `prune(max_age_days=...)` |
| **Cross-session coordination** | Yes — via `CrossSessionCoordinator` | No | Yes |
| **Security / classification** | Rate limiting via `RateLimiter`; API key auth via `APIKeyAuth` | File validation via `ClaudeMemoryConfig.validate_files` | Full classification system (`Classification`, `PIIScrubber`, `SecretsDetector`, audit logging) |
| **Setup complexity** | Requires Redis; use `is_redis_available()` to check before connecting | Zero infrastructure — reads `.claude/CLAUDE.md` from disk | Requires `ControlPanelConfig` and optionally Redis; managed via `MemoryControlPanel` |
| **Railway deployment** | `get_railway_redis()` — raises `OSError` if `REDIS_URL` is missing | Not applicable | Not applicable |
| **Observability** | `get_stats()`, `check_redis_connection()` | `get_loaded_files()` | `MemoryControlPanel.get_statistics()`, `health_check()` |
| **Import depth control** | No | Yes — `ClaudeMemoryConfig.max_import_depth` (default: 5) | No |
| **Max file size guard** | No | Yes — `ClaudeMemoryConfig.max_file_size_bytes` (default: 1 000 000) | No |

## Key tradeoffs

**Redis short-term memory** is the fastest path to keyed storage with expiry. `stash`, `retrieve`, `delete`, and `keys` map directly onto Redis primitives, so latency is as low as your Redis instance allows. The tradeoff is infrastructure: you must have Redis running (verify with `is_redis_available()`), and the `get_railway_redis()` helper will raise an `OSError` at startup if `REDIS_URL` is absent from the environment. There is no semantic search — if you need to query by meaning rather than exact key, this backend cannot help.

**Claude file memory** (`ClaudeMemoryLoader`) has zero infrastructure requirements and is the only option that sources context directly from `CLAUDE.md` files on disk. `load_all_memory(project_root)` walks the project tree up to `max_import_depth` levels and concatenates content for injection into agent context. Because it reads files, it is inherently read-heavy and not suitable for high-frequency writes or real-time coordination between agents.

**Enterprise pattern storage** (`MemDocsStorage`, surfaced through `MemoryControlPanel`) is the only option that offers semantic search via `SearchableMemoryBackend.search`, structured promotion (`promote`), and compliance-grade classification (`PIIScrubber`, `SecretsDetector`, `AuditLogger`). It is also the most operationally heavy: `ControlPanelConfig` requires configuring `redis_host`, `redis_port`, `storage_dir`, and `audit_dir`. Use `MemoryControlPanel.health_check()` and `get_statistics()` to monitor it.

## Use X when...

**Use `RedisShortTermMemory` (via `get_redis_memory()`) when:**
- You need fast keyed reads and writes with optional TTL expiry during a single agent session or deployment.
- You are coordinating multiple agents in real-time — `supports_realtime()` and `supports_distributed()` both return `True`.
- You are deploying to Railway and can guarantee `REDIS_URL` is set in the environment.

**Use `ClaudeMemoryLoader` (via `ClaudeMemoryConfig`) when:**
- You want to inject project-level or user-level context from `CLAUDE.md` files into an agent without any infrastructure.
- You need to control which memory levels load — `load_enterprise`, `load_user`, and `load_project` are individually togglable in `ClaudeMemoryConfig`.
- You are bootstrapping a new project and want a starter file — call `create_default_project_memory(project_root)`.

**Use `MemoryControlPanel` / `MemDocsStorage` when:**
- You need semantic search over stored patterns — no other backend exposes `search(query, limit, **filters)`.
- Your environment has compliance requirements: PII scrubbing, secret detection, audit logging, and `Classification`-based access control are only available here.
- You need long-term pattern retention with pruning by age (`prune(max_age_days=...)`) and bulk export (`export_patterns(output_path)`).
- You are operating at enterprise scale and need `MemoryControlPanel.status()`, `health_check()`, and `get_statistics()` for operational visibility.

**Do not use the memory subsystem directly when:**
- Your problem spans multiple features and belongs in an orchestration layer above individual backends.
- You need behavior not exposed by `MemoryBackend` or `SearchableMemoryBackend` — propose an extension point rather than patching internals.

## Source files

- `src/attune/memory/**`

**Tags:** `memory`, `storage`
