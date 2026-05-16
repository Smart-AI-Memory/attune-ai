---
type: architecture
name: memory
tags: [memory, storage, security, redis, architecture]
---

# Memory architecture

## Purpose

The memory subsystem stores, retrieves, and secures agent knowledge across two durability tiers: short-term (Redis-backed, TTL-scoped, session-aware) and long-term (MemDocs-backed, classified, pattern-lifecycle-managed). It also loads static CLAUDE.md files that Claude Code uses as persistent project rules. The subsystem does **not** handle conversation history (Claude manages that natively), help-system template rendering, or cross-linking between documentation templates — those live in `transformers.py` and `build_cross_links.py` respectively.

## Key classes

This table covers the architecturally significant classes. For the full inventory of ~90 classes, see the source files listed in each row.

| Class | Responsibility | File |
|-------|---------------|------|
| `MemoryBackend` | Protocol that every short-term backend must satisfy: `stash`, `retrieve`, `delete`, `keys`, `is_connected`, `get_stats`, `close`, `supports_realtime`, `supports_distributed`. | `src/attune/memory/backend.py` |
| `SearchableMemoryBackend` | Extends `MemoryBackend` with `search` (full-text + filter) and `promote` (advances a session's staged patterns into broader visibility). | `src/attune/memory/backend.py` |
| `RedisShortTermMemory` | Facade that composes `BaseOperations`, `BatchOperations`, `CacheManager`, `PatternStaging`, `SessionManager`, `PubSubManager`, `StreamManager`, and seven other mixins into the primary short-term backend. Satisfies `SearchableMemoryBackend`. | `src/attune/memory/short_term/facade.py` |
| `UnifiedMemory` | Top-level entry point; assembles a short-term backend and a long-term backend via seven `*Mixin` classes (`BackendInitMixin`, `ShortTermOperationsMixin`, `LongTermOperationsMixin`, `PatternPromotionMixin`, `LifecycleMixin`, `CapabilitiesMixin`, `HandoffAndExportMixin`). Callers interact with this class, not the backends directly. | `src/attune/memory/unified.py` |
| `LongTermMemory` / `MemDocsStorage` | Simplified persistent storage interface and its default mock/file backend; together they implement the long-term tier. | `src/attune/memory/simple_storage.py`, `src/attune/memory/storage_backend.py` |
| `SecureMemDocsIntegration` | Bridges `ClaudeMemoryLoader` output and `MemDocsStorage`; enforces classification rules, runs PII scrubbing, and logs audit events before any pattern is persisted. | `src/attune/memory/long_term_integration.py` |
| `ClaudeMemoryLoader` | Discovers, loads, and caches CLAUDE.md files from enterprise, user, and project levels (up to `max_import_depth`). Outputs merged content, not structured records. | `src/attune/memory/claude_memory.py` |
| `MemoryControlPanel` | Enterprise admin surface: starts/stops Redis, lists/deletes patterns, clears short-term memory, exports patterns, and runs health checks. Not in the read/write hot path. | `src/attune/memory/control_panel.py` |
| `MemoryAPIHandler` | HTTP handler (`do_GET`, `do_POST`, `do_DELETE`, `do_OPTIONS`) that exposes `MemoryControlPanel` operations over a local REST API. Handles CORS and delegates auth/rate-limiting to support classes. | `src/attune/memory/control_panel_api.py` |
| `RateLimiter` | IP-windowed rate limiter (sliding window, configurable max requests) used by `MemoryAPIHandler` to protect the control panel API. | `src/attune/memory/control_panel_support.py` |
| `APIKeyAuth` | Validates bearer tokens for the control panel API; no-ops when no key is configured. | `src/attune/memory/control_panel_support.py` |
| `PIIScrubber` | Detects and redacts PII before storage using regex-based `PIIPattern` definitions; invoked by `SecureMemDocsIntegration` on SENSITIVE-classified writes. | `src/attune/memory/security/pii_scrubber.py` |
| `SecretsDetector` | Detects credentials, tokens, and high-entropy strings via pattern matching and entropy analysis; raises `SecurityError` to abort storage if a secret is found. | `src/attune/memory/security/secrets_detector.py` |
| `AuditLogger` | Persists structured `AuditEvent` records for every classified memory operation; composed from `AuditLogMethodsMixin`, `AuditQueryMixin`, and `AuditReportMixin`. | `src/attune/memory/security/audit_logger.py` |
| `EncryptionManager` | Encrypts and decrypts SENSITIVE-tier patterns at rest. Optional dependency; `MemoryFeatures` reports whether it is available. | `src/attune/memory/encryption.py` |
| `CrossSessionCoordinator` | Manages agent registration, heartbeats, and conflict negotiation via Redis pub/sub (`CHANNEL_SESSIONS`, `KEY_ACTIVE_AGENTS`). Used by `BackgroundService`. | `src/attune/memory/cross_session/coordinator.py` |
| `MemoryGraph` | Knowledge graph (`Node`/`Edge`) for cross-workflow intelligence; nodes are typed (`BugNode`, `VulnerabilityNode`, `PatternNode`, etc.) and connected by typed `EdgeType` relationships. | `src/attune/memory/graph.py` |
| `Classification` | Three-tier enum (`PUBLIC`, `INTERNAL`, `SENSITIVE`) applied to every stored pattern; drives encryption, PII scrubbing, and audit logging decisions throughout the long-term tier. | `src/attune/memory/long_term_types.py` |
| `MemoryFeatures` | Probes optional dependencies at runtime and exposes `FeatureInfo` records so callers can gate on Redis, encryption, or distributed-mode availability without importing those modules. | `src/attune/memory/features.py` |

## Data flow

### Short-term write (agent stores a value)

```
Agent
  │  stash(key, value, ttl, agent_id)
  ▼
UnifiedMemory  (ShortTermOperationsMixin)
  │
  ▼
RedisShortTermMemory  (facade)
  ├── DataSanitizer          checks for secrets / sanitizes input
  ├── BaseOperations         SET key in Redis with TTL
  ├── CacheManager           updates local LRU cache
  └── StreamManager          appends audit event to Redis Stream
```

### Long-term write (pattern promoted to MemDocs)

```
Agent / UnifiedMemory  (PatternPromotionMixin)
  │  store pattern with classification + pattern_type
  ▼
SecureMemDocsIntegration
  ├── SecretsDetector        abort if secret found  ──► SecurityError
  ├── PIIScrubber            redact PII for SENSITIVE tier
  ├── EncryptionManager      encrypt value for SENSITIVE tier
  ├── ClassificationRules    enforce access-tier constraints
  ├── AuditLogger            write AuditEvent record
  └── MemDocsStorage / LongTermMemory   persist SecurePattern
```

### CLAUDE.md load (project rules injected into context)

```
ClaudeMemoryConfig
  (enabled, load_enterprise, load_user, load_project,
   max_import_depth, max_file_size_bytes)
  │
  ▼
ClaudeMemoryLoader.load_all_memory(project_root)
  ├── discovers enterprise  ~/.attune/CLAUDE.md
  ├── discovers user        ~/CLAUDE.md
  └── discovers project     <project_root>/.claude/CLAUDE.md
        │  follows @import directives up to max_import_depth
        ▼
  merged string  ──►  SecureMemDocsIntegration (optional)
                 ──►  caller (Claude Code context injection)
```

### Cross-session coordination

```
BackgroundService  (daemon thread)
  │  polls Redis every HEARTBEAT_INTERVAL_SECONDS
  ▼
CrossSessionCoordinator
  ├── KEY_ACTIVE_AGENTS      registry of live agent IDs
  ├── KEY_SERVICE_LOCK       distributed leader election
  ├── CHANNEL_SESSIONS       pub/sub for session events
  └── ConflictNegotiation    resolves write conflicts via ConflictStrategy
```

### Control panel API

```
HTTP client
  │  GET/POST/DELETE  localhost:8765
  ▼
MemoryAPIHandler
  ├── APIKeyAuth             validate bearer token
  ├── RateLimiter            enforce per-IP window
  └── MemoryControlPanel
        ├── status / health_check
        ├── list_patterns / delete_pattern / export_patterns
        └── start_redis / stop_redis / clear_short_term
```

## Design decisions

### `UnifiedMemory` assembled from mixins, not inheritance

`UnifiedMemory` composes seven `*Mixin` classes (`BackendInitMixin`, `ShortTermOperationsMixin`, `LongTermOperationsMixin`, `PatternPromotionMixin`, `LifecycleMixin`, `CapabilitiesMixin`, `HandoffAndExportMixin`) rather than inheriting from `RedisShortTermMemory` or `LongTermMemory` directly. This keeps each mixin independently testable and prevents the short-term and long-term tiers from coupling. The cost is that `UnifiedMemory`'s MRO is non-trivial; when debugging method resolution, check `unified.py` and the `mixins/` directory together.

### `RedisShortTermMemory` as a composed facade

The short-term tier splits across fifteen classes (`BaseOperations`, `BatchOperations`, `CacheManager`, `PatternStaging`, `SessionManager`, `PubSubManager`, `StreamManager`, `TimelineManager`, `TransactionManager`, `WorkingMemory`, `ConflictNegotiation`, `CrossSessionManager`, `QueueManager`, `Pagination`, `DataSanitizer`) and composes them into a single `RedisShortTermMemory` facade. A monolithic Redis class was rejected because each capability group (streaming, pub/sub, queuing, pagination) has distinct test and configuration concerns. Adding a new Redis capability means adding a new file in `src/attune/memory/short_term/` and composing it into the facade — not modifying existing classes.

### `Classification` as a cross-cutting invariant

Rather than letting callers decide when to encrypt or scrub PII, `SecureMemDocsIntegration` enforces those decisions based on the `Classification` enum value attached to every pattern. `SENSITIVE` always triggers `PIIScrubber` + `EncryptionManager` + `AuditLogger`; `INTERNAL` triggers `AuditLogger` only; `PUBLIC` writes straight through. This means classification is a contract, not a hint — changing a pattern's tier changes its entire storage path.

### Optional Redis with file-based fallback

`MemoryFeatures` and `is_redis_available()` probe for Redis at runtime. When Redis is absent, `FileSessionMemory` (backed by `FileSessionConfig`, `PersistenceMixin`, `PatternStagingMixin`) provides session storage on disk under `~/.attune/memory/`. The two backends satisfy the same `MemoryBackend` protocol, so `UnifiedMemory` switches between them without conditional logic in the callers.

## Extension points

- **Add a new short-term backend** (e.g., Memcached): implement `MemoryBackend` (or `SearchableMemoryBackend` for search support) and pass an instance to `UnifiedMemory` via `MemoryConfig`. You do not need to touch `RedisShortTermMemory` or the facade.

- **Add a new Redis capability** (e.g., geo queries): create a new operations class in `src/attune/memory/short_term/`, inherit from it in `RedisShortTermMemory` in `facade.py`, and add the corresponding mixin to `UnifiedMemory` if you need to expose it at the top level.

- **Add a new node type to the memory graph**: subclass `Node` in `src/attune/memory/nodes.py` (following `BugNode`, `VulnerabilityNode`, `PatternNode`), and add the corresponding `NodeType` enum value. Register any new edge relationships in `EdgeType` in `edges.py`.

- **Add a new classification-based security rule**: extend `ClassificationRules` in `src/attune/memory/long_term_types.py` and update `SecureMemDocsIntegration` to apply the rule in its write pipeline. All existing callers inherit the enforcement automatically.

- **Add a new CLAUDE.md discovery level**: extend `ClaudeMemoryLoader.load_all_memory()` and add the corresponding flag to `ClaudeMemoryConfig`. The `max_import_depth` guard already applies to any level you add.

- **Expose a new control panel operation over HTTP**: add the method to `MemoryControlPanel`, then add a route in `MemoryAPIHandler.do_GET` / `do_POST` / `do_DELETE`. `RateLimiter` and `APIKeyAuth` apply automatically to all routes.

For usage — operations, storage behavior, and search syntax — see `references/skill-memory-and-context.md`.
