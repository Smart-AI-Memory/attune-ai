---
type: reference
name: memory-reference
feature: memory
depth: reference
generated_at: 2026-06-12T00:20:52.589323+00:00
source_hash: 439162c85525d4aff627199f05d3f52d259589b86b947c5b2f62b832a0d15fae
status: generated
scaffold_hash: 8c6258d4a61cd8f4917baaa8a00c3f4054394b40ba97c4386f7c2f7279eb584f
---

# Memory reference

Layered storage API for Attune AI agents. Use `MemoryBackend` and `SearchableMemoryBackend` to write short-term data and recall it by semantic query. Use `UnifiedMemory` to combine short-term Redis storage with long-term MemDocs pattern storage in a single interface. Use `ClaudeMemoryLoader` to inject project-level CLAUDE.md files into agent context. Use `MemoryControlPanel` to administer Redis, inspect patterns, and export audit data. The security subpackage provides PII scrubbing, secrets detection, and audit logging. Version: `2.2.0`.

## Classes

| Class | Description | File |
|-------|-------------|------|
| `MemoryBackend` | Protocol for short-term memory backends. | `src/attune/memory/backend.py` |
| `SearchableMemoryBackend` | Extended protocol for backends with semantic search. | `src/attune/memory/backend.py` |
| `ClaudeMemoryConfig` | Configuration for Claude memory integration. | `src/attune/memory/claude_memory.py` |
| `MemoryFile` | Represents a loaded CLAUDE.md memory file. | `src/attune/memory/claude_memory.py` |
| `ClaudeMemoryLoader` | Loads and manages Claude Code memory files (CLAUDE.md). | `src/attune/memory/claude_memory.py` |
| `ControlPanelConfig` | Configuration for the memory control panel. | `src/attune/memory/control_panel.py` |
| `MemoryControlPanel` | Enterprise control panel for Empathy memory management. | `src/attune/memory/control_panel.py` |
| `MemoryAPIHandler` | HTTP request handler for the Memory Control Panel API. | `src/attune/memory/control_panel_api.py` |
| `RateLimiter` | Simple in-memory rate limiter by IP address. | `src/attune/memory/control_panel_support.py` |
| `APIKeyAuth` | Simple API key authentication. | `src/attune/memory/control_panel_support.py` |
| `MemoryStats` | Statistics for the memory system. | `src/attune/memory/control_panel_support.py` |
| `CrossSessionCoordinator` | Coordinator for cross-session agent communication. | `src/attune/memory/cross_session/coordinator.py` |
| `SessionType` | Type of session/agent. | `src/attune/memory/cross_session/models.py` |
| `ConflictStrategy` | Strategy for resolving conflicts between agents. | `src/attune/memory/cross_session/models.py` |
| `SessionInfo` | Information about an active session. | `src/attune/memory/cross_session/models.py` |
| `ConflictResult` | Result of a conflict resolution. | `src/attune/memory/cross_session/models.py` |
| `BackgroundService` | Background service daemon for cross-session coordination. | `src/attune/memory/cross_session/service.py` |
| `EdgeType` | Types of relationships between memory-graph nodes. | `src/attune/memory/edges.py` |
| `Edge` | An edge connecting two nodes in the memory graph. | `src/attune/memory/edges.py` |
| `EncryptionManager` | Manages encryption and decryption for `SENSITIVE` patterns. | `src/attune/memory/encryption.py` |
| `FeatureStatus` | Status of an optional memory feature. | `src/attune/memory/features.py` |
| `FeatureInfo` | Information about a memory feature. | `src/attune/memory/features.py` |
| `MemoryFeatures` | Check availability of memory subsystem features. | `src/attune/memory/features.py` |
| `FileSessionMemory` | File-based session memory with persistence. | `src/attune/memory/file_session.py` |
| `FileSessionConfig` | Configuration for file-based session memory. | `src/attune/memory/file_session_models.py` |
| `WorkingEntry` | Entry in working memory. | `src/attune/memory/file_session_models.py` |
| `StagedPatternFile` | Pattern staged for validation (file-based). | `src/attune/memory/file_session_models.py` |
| `SessionState` | Complete state of a session. | `src/attune/memory/file_session_models.py` |
| `PatternStagingMixin` | Mixin providing pattern staging operations. | `src/attune/memory/file_session_patterns.py` |
| `PersistenceMixin` | Mixin providing session persistence operations. | `src/attune/memory/file_session_persistence.py` |
| `FileStashBackend` | Searchable, zero-infrastructure session stash backed by a local JSONL file. | `src/attune/memory/file_stash.py` |
| `MemoryGraph` | Knowledge graph for cross-workflow intelligence. | `src/attune/memory/graph.py` |
| `LessonsManager` | Manages lessons learned from previous sessions. | `src/attune/memory/lessons.py` |
| `SecureMemDocsIntegration` | Secure integration between Claude Memory and MemDocs. | `src/attune/memory/long_term_integration.py` |
| `PatternOperationsMixin` | Mixin providing pattern list, delete, and statistics operations. | `src/attune/memory/long_term_operations.py` |
| `PatternPipelineMixin` | Mixin providing store/retrieve pipeline helpers. | `src/attune/memory/long_term_pipelines.py` |
| `Classification` | Three-tier classification system for MemDocs patterns. | `src/attune/memory/long_term_types.py` |
| `ClassificationRules` | Security rules for each classification level. | `src/attune/memory/long_term_types.py` |
| `PatternMetadata` | Metadata for stored MemDocs patterns. | `src/attune/memory/long_term_types.py` |
| `SecurePattern` | Represents a securely stored pattern. | `src/attune/memory/long_term_types.py` |
| `SecurityError` | Raised when a security policy is violated. | `src/attune/memory/long_term_types.py` |
| `MemoryPermissionError` | Raised when access is denied. | `src/attune/memory/long_term_types.py` |
| `AttuneMemoryTool` | Anthropic Memory tool backed by an attune `MemoryBackend`. | `src/attune/memory/memory_tool.py` |
| `BackendInitMixin` | Mixin providing backend initialization for `UnifiedMemory`. | `src/attune/memory/mixins/backend_init_mixin.py` |
| `CapabilitiesMixin` | Mixin providing capability detection and health checks for `UnifiedMemory`. | `src/attune/memory/mixins/capabilities_mixin.py` |
| `HandoffAndExportMixin` | Mixin providing session handoff and export for `UnifiedMemory`. | `src/attune/memory/mixins/handoff_mixin.py` |
| `LifecycleMixin` | Mixin providing lifecycle management for `UnifiedMemory`. | `src/attune/memory/mixins/lifecycle_mixin.py` |
| `LongTermOperationsMixin` | Mixin providing long-term memory operations for `UnifiedMemory`. | `src/attune/memory/mixins/long_term_mixin.py` |
| `PatternPromotionMixin` | Mixin providing pattern promotion for `UnifiedMemory`. | `src/attune/memory/mixins/promotion_mixin.py` |
| `ShortTermOperationsMixin` | Mixin providing short-term memory operations for `UnifiedMemory`. | `src/attune/memory/mixins/short_term_mixin.py` |
| `NodeType` | Types of nodes in the memory graph. | `src/attune/memory/nodes.py` |
| `Node` | A node in the memory graph. | `src/attune/memory/nodes.py` |
| `BugNode` | Specialized node for bugs. | `src/attune/memory/nodes.py` |
| `VulnerabilityNode` | Specialized node for security vulnerabilities. | `src/attune/memory/nodes.py` |
| `PerformanceNode` | Specialized node for performance issues. | `src/attune/memory/nodes.py` |
| `PatternNode` | Specialized node for code patterns. | `src/attune/memory/nodes.py` |
| `PersonalMemory` | Store and retrieve personal cross-session memory. | `src/attune/memory/personal.py` |
| `RedisDetectionResult` | Result of Redis auto-detection. | `src/attune/memory/redis_auto_detect.py` |
| `RedisAutoDetector` | Auto-detect Redis availability and manage user preferences. | `src/attune/memory/redis_auto_detect.py` |
| `RedisStartMethod` | Methods for starting Redis, in order of preference. | `src/attune/memory/redis_bootstrap.py` |
| `RedisStatus` | Status of a Redis connection or startup attempt. | `src/attune/memory/redis_bootstrap.py` |
| `AuditLogger` | Comprehensive audit logging for Attune AI. | `src/attune/memory/security/audit_logger.py` |
| `AuditEvent` | Represents a single audit event. | `src/attune/memory/security/events.py` |
| `SecurityViolation` | Represents a security policy violation. | `src/attune/memory/security/events.py` |
| `AuditLogMethodsMixin` | Mixin that adds event-specific logging methods to `AuditLogger`. | `src/attune/memory/security/log_methods.py` |
| `PIIDetection` | Details about a detected PII instance. | `src/attune/memory/security/pii_scrubber.py` |
| `PIIPattern` | Definition of a PII detection pattern. | `src/attune/memory/security/pii_scrubber.py` |
| `PIIScrubber` | Comprehensive PII detection and scrubbing system. | `src/attune/memory/security/pii_scrubber.py` |
| `AuditQueryMixin` | Mixin that adds query capabilities to `AuditLogger`. | `src/attune/memory/security/query.py` |
| `AuditReportMixin` | Mixin that adds reporting capabilities to `AuditLogger`. | `src/attune/memory/security/reports.py` |
| `SecretsDetector` | Detects secrets using pattern matching and entropy analysis. | `src/attune/memory/security/secrets_detector.py` |
| `SecretType` | Types of secrets that can be detected. | `src/attune/memory/security/secrets_types.py` |
| `Severity` | Severity levels for secret detections. | `src/attune/memory/security/secrets_types.py` |
| `SecretDetection` | Metadata about a detected secret. | `src/attune/memory/security/secrets_types.py` |
| `SessionStashEntry` | A single raw cross-session finding awaiting recall or promotion. | `src/attune/memory/session_stash.py` |
| `BaseOperations` | CRUD operations and connection management for short-term memory. | `src/attune/memory/short_term/base.py` |
| `BatchOperations` | Batch operations using Redis pipelines. | `src/attune/memory/short_term/batch.py` |
| `CacheManager` | Local LRU cache manager for two-tier caching. | `src/attune/memory/short_term/caching.py` |
| `ConflictNegotiation` | Conflict context and resolution operations. | `src/attune/memory/short_term/conflicts.py` |
| `CrossSessionManager` | Cross-session coordination operations. | `src/attune/memory/short_term/cross_session.py` |
| `RedisShortTermMemory` | Facade composing all short-term memory operations. | `src/attune/memory/short_term/facade.py` |
| `Pagination` | SCAN-based pagination operations. | `src/attune/memory/short_term/pagination.py` |
| `PatternStaging` | Pattern staging lifecycle operations. | `src/attune/memory/short_term/patterns.py` |
| `PubSubManager` | Real-time publish/subscribe operations. | `src/attune/memory/short_term/pubsub.py` |
| `QueueManager` | Redis list operations for task queues. | `src/attune/memory/short_term/queues.py` |
| `DataSanitizer` | Data sanitization for short-term memory. | `src/attune/memory/short_term/security.py` |
| `SessionManager` | Collaboration session operations. | `src/attune/memory/short_term/sessions.py` |
| `StreamManager` | Redis Streams operations for audit trails and event logs. | `src/attune/memory/short_term/streams.py` |
| `TimelineManager` | Redis sorted set operations for timeline queries. | `src/attune/memory/short_term/timelines.py` |
| `TransactionManager` | Atomic operations using Redis transactions. | `src/attune/memory/short_term/transactions.py` |
| `WorkingMemory` | Working memory operations for agent data storage. | `src/attune/memory/short_term/working.py` |
| `LongTermMemory` | Simplified long-term persistent storage interface. | `src/attune/memory/simple_storage.py` |
| `MemDocsStorage` | Mock/simple MemDocs storage backend. | `src/attune/memory/storage_backend.py` |
| `AgentContext` | Compact context package for sub-agent handoff. | `src/attune/memory/summary_index.py` |
| `ConversationSummaryIndex` | Redis-backed conversation summary with topic indexing. | `src/attune/memory/summary_index.py` |
| `AccessTier` | Role-based access tiers per EMPATHY_PHILOSOPHY.md. | `src/attune/memory/types.py` |
| `TTLStrategy` | TTL strategies for different memory types. | `src/attune/memory/types.py` |
| `RedisConfig` | Enhanced Redis configuration with SSL and retry support. | `src/attune/memory/types.py` |
| `RedisMetrics` | Metrics for Redis operations. | `src/attune/memory/types.py` |
| `PaginatedResult` | Result of a paginated query. | `src/attune/memory/types.py` |
| `TimeWindowQuery` | Query parameters for time-window operations. | `src/attune/memory/types.py` |
| `AgentCredentials` | Agent identity and access permissions. | `src/attune/memory/types.py` |
| `StagedPattern` | Pattern awaiting validation. | `src/attune/memory/types.py` |
| `ConflictContext` | Context for principled negotiation. | `src/attune/memory/types.py` |
| `SecurityError` | Raised when a security policy is violated (e.g., secrets detected in data). | `src/attune/memory/types.py` |
| `Environment` | Deployment environment for storage configuration. | `src/attune/memory/unified.py` |
| `MemoryConfig` | Configuration for the unified memory system. | `src/attune/memory/unified.py` |
| `UnifiedMemory` | Unified interface for short-term and long-term memory. | `src/attune/memory/unified.py` |

### `MemoryBackend`

`MemoryBackend` is the protocol every short-term storage backend must implement. Pass any conforming backend to `UnifiedMemory`, `AttuneMemoryTool`, or `make_memory_tool`.

#### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `stash` | `key: str, value: Any, ttl: int \| None = None, agent_id: str \| None = None` | `bool` | Write a value; returns `True` on success. |
| `retrieve` | `key: str, agent_id: str \| None = None` | `Any \| None` | Read a value by key, or `None` if absent. |
| `delete` | `key: str` | `bool` | Remove a key; returns `True` on success. |
| `keys` | `pattern: str = '*'` | `list[str]` | List keys matching a glob pattern. |
| `is_connected` | — | `bool` | Return `True` when the backend is reachable. |
| `get_stats` | — | `dict` | Return backend-specific statistics. |
| `close` | — | `None` | Release the backend connection. |
| `supports_realtime` | — | `bool` | Return `True` if the backend supports pub/sub. |
| `supports_distributed` | — | `bool` | Return `True` if the backend supports distributed access. |

### `SearchableMemoryBackend`

`SearchableMemoryBackend` extends `MemoryBackend` with semantic search, session promotion, and pruning. Use it anywhere you need `search` or `remember` in addition to the base CRUD operations.

#### Methods

Inherits all `MemoryBackend` methods, plus:

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `search` | `query: str, limit: int = 10, **filters: Any` | `list[dict]` | Semantic search over stored memory. |
| `remember` | `content: str, *, memory_id: str \| None = None, session_id: str \| None = None, topics: list[str] \| None = None` | `bool` | Store content with optional topic metadata. |
| `promote` | `session_id: str \| None = None` | `bool` | Promote session memory to long-term storage. |
| `prune` | `max_age_days: int \| None = None` | `int` | Remove stale entries; returns the count removed. |
| `recent` | `limit: int = 5, **filters: Any` | `list[dict]` | Return the most-recent entries, newest first. |

### `ClaudeMemoryConfig`

Configuration for Claude memory integration. Controls which CLAUDE.md files are loaded and imposes safety limits on file size and import depth.

#### Fields

| Field | Type | Default |
|-------|------|---------|
| `enabled` | `bool` | `False` |
| `load_enterprise` | `bool` | `True` |
| `load_user` | `bool` | `True` |
| `load_project` | `bool` | `True` |
| `enterprise_memory_path` | `str \| None` | `None` |
| `project_root` | `str \| None` | `None` |
| `max_import_depth` | `int` | `5` |
| `max_file_size_bytes` | `int` | `1000000` |
| `validate_files` | `bool` | `True` |

### `MemoryFile`

Represents a loaded CLAUDE.md memory file with its content and import graph.

#### Fields

| Field | Type | Default |
|-------|------|---------|
| `level` | `str` | — |
| `path` | `str` | — |
| `content` | `str` | — |
| `imports` | `list[str]` | `field(default_factory=list)` |
| `load_order` | `int` | `0` |

### `ControlPanelConfig`

Configuration for the memory control panel, including Redis connection details and storage paths.

#### Fields

| Field | Type | Default |
|-------|------|---------|
| `redis_host` | `str` | `'localhost'` |
| `redis_port` | `int` | `6379` |
| `storage_dir` | `str` | `'./memdocs_storage'` |
| `audit_dir` | `str` | `'./logs'` |
| `auto_start_redis` | `bool` | `True` |

### `ClaudeMemoryLoader`

Loads and manages Claude Code memory files (CLAUDE.md).

#### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__` | `config: ClaudeMemoryConfig \| None = None` | — | Initialize the loader with optional config. |
| `load_all_memory` | `project_root: str \| None = None` | `str` | Load and concatenate all CLAUDE.md files into a single string. |
| `clear_cache` | — | — | Clear the in-memory file cache. |
| `get_loaded_files` | — | `list[str]` | Return paths of all currently loaded memory files. |

### `MemoryControlPanel`

Enterprise control panel for Empathy memory management. Gives you operational control over Redis, stored patterns, and short-term memory.

#### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__` | `config: ControlPanelConfig \| None = None` | — | Initialize the panel with optional config. |
| `status` | — | `dict[str, Any]` | Return current panel and Redis status. |
| `start_redis` | `verbose: bool = True` | `RedisStatus` | Start Redis and return its status. |
| `stop_redis` | — | `bool` | Stop Redis; returns `True` on success. |
| `get_statistics` | — | `MemoryStats` | Return memory usage statistics. |
| `list_patterns` | `classification: str \| None = None, limit: int = 100` | `list[dict[str, Any]]` | List stored patterns, optionally filtered by classification. |
| `delete_pattern` | `pattern_id: str, user_id: str = 'admin@system'` | `bool` | Delete a pattern by ID. |
| `clear_short_term` | `agent_id: str = 'admin'` | `int` | Clear short-term memory for an agent; returns the count removed. |
| `export_patterns` | `output_path: str, classification: str \| None = None` | `int` | Export patterns to a file; returns the count exported. |
| `health_check` | — | `dict[str, Any]` | Run a health check and return results. |

### `RateLimiter`

Sliding-window, in-memory rate limiter keyed by client IP address.

#### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__` | `window_seconds: int = 60, max_requests: int = 100` | — | Initialize with sliding-window parameters. |
| `is_allowed` | `client_ip: str` | `bool` | Return `True` when the client IP is within its rate limit. |
| `get_remaining` | `client_ip: str` | `int` | Return the number of requests remaining for the client IP in the current window. |

### `APIKeyAuth`

Single-key API authentication for the Memory Control Panel.

#### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__` | `api_key: str \| None = None` | — | Initialize with an optional API key. |
| `is_valid` | `provided_key: str \| None` | `bool` | Return `True` when the provided key matches the configured key. |

## Functions

| Function | Parameters | Returns | Description | File |
|----------|-----------|---------|-------------|------|
| `is_redis_available` | — | `bool` | Check whether the Redis subsystem is available without importing it. | `src/attune/memory/__init__.py` |
| `create_default_project_memory` | `project_root: str, framework: str = 'empathy'` | — | Create a default `.claude/CLAUDE.md` file for a project. | `src/attune/memory/claude_memory.py` |
| `parse_redis_url` | `url: str` | `dict` | Parse a Redis URL into connection parameters. | `src/attune/memory/config.py` |
| `get_redis_config` | — | `dict` | Return Redis configuration from environment variables (legacy dict API). | `src/attune/memory/config.py` |
| `get_redis_memory` | `url: str \| None = None, use_mock: bool \| None = None` | `RedisShortTermMemory` | Create a `RedisShortTermMemory` instance using environment-based config. | `src/attune/memory/config.py` |
| `check_redis_connection` | — | `dict` | Check the Redis connection and return its status. | `src/attune/memory/config.py` |
| `get_railway_redis` | — | `RedisShortTermMemory` | Return Redis configured for Railway deployment. | `src/attune/memory/config.py` |
| `run_api_server` | `panel: MemoryControlPanel, host: str = 'localhost', port: int = 8765, api_key: str \| None = None, enable_rate_limit: bool = True, rate_limit_requests: int = 100, rate_limit_window: int = 60, ssl_certfile: str \| None = None, ssl_keyfile: str \| None = None, allowed_origins: list[str] \| None = None` | — | Run the Memory API server with security features enabled. | `src/attune/memory/control_panel_api.py` |
| `print_status` | `panel: MemoryControlPanel` | — | Print panel status in formatted output. | `src/attune/memory/control_panel_display.py` |
| `print_stats` | `panel: MemoryControlPanel` | — | Print memory statistics in formatted output. | `src/attune/memory/control_panel_display.py` |
| `print_health` | `panel: MemoryControlPanel` | — | Print the health check results in formatted output. | `src/attune/memory/control_panel_display.py` |
| `main` | — | — | CLI entry point for the control panel. | `src/attune/memory/control_panel_display.py` |
| `resolve_by_priority` | `agent_id: str, access_tier: AccessTier, session_info: SessionInfo, resource_key: str, other_session: SessionInfo \| None` | `ConflictResult` | Resolve a resource conflict using access-tier priority. | `src/attune/memory/cross_session/conflicts.py` |
| `resolve_first_write` | `agent_id: str, client: Any, resource_key: str, other_session: SessionInfo \| None` | `ConflictResult` | Resolve a conflict using first-write-wins. | `src/attune/memory/cross_session/conflicts.py` |
| `resolve_last_write` | `agent_id: str, resource_key: str, other_session: SessionInfo \| None` | `ConflictResult` | Resolve a conflict using last-write-wins. | `src/attune/memory/cross_session/conflicts.py` |
| `generate_agent_id` | `session_type: SessionType` | `str` | Generate a unique agent ID for the given session type. | `src/attune/memory/cross_session/models.py` |
| `check_redis_cross_session_support` | `memory: RedisShortTermMemory` | `bool` | Check whether Redis supports cross-session communication. | `src/attune/memory/cross_session/service.py` |
| `get_or_start_service` | `memory: RedisShortTermMemory` | `BackgroundService \| None` | Return the running background service, or start one if none exists. | `src/attune/memory/cross_session/service.py` |
| `get_file_session_memory` | `user_id: str, base_dir: str = '.attune', **kwargs: Any` | `FileSessionMemory` | Create a file-based session memory instance for a user. | `src/attune/memory/file_session.py` |
| `classify_pattern` | `content: str, pattern_type: str` | `Classification` | Auto-classify a pattern based on its content and type. | `src/attune/memory/long_term_classification.py` |
| `check_access` | `user_id: str, classification: Classification, metadata: dict[str, Any]` | `bool` | Return `True` when the user has access to a pattern at the given classification level. | `src/attune/memory/long_term_classification.py` |
| `make_memory_tool` | `backend: MemoryBackend \| None = None, *, root: str = _DEFAULT_ROOT, user_id: str \| None = None` | `Any` | Build an Anthropic Memory-tool instance backed by an attune backend. | `src/attune/memory/memory_tool.py` |
| `auto_detect_redis` | — | `RedisDetectionResult` | Auto-detect Redis availability. | `src/attune/memory/redis_auto_detect.py` |
| `ensure_redis` | `host: str = 'localhost', port: int = 6379, auto_start: bool = True, verbose: bool = True` | `RedisStatus` | Ensure Redis is available, starting it if necessary. | `src/attune/memory/redis_bootstrap.py` |
| `stop_redis` | `method: RedisStartMethod` | `bool` | Stop Redis if this process started it; returns `True` on success. | `src/attune/memory/redis_bootstrap.py` |
| `get_redis_or_mock` | `host: str = 'localhost', port: int = 6379` | — | Return a Redis connection, starting Redis if needed, or fall back to a mock. | `src/attune/memory/redis_bootstrap.py` |
| `detect_secrets` | `content: str, **kwargs` | `list[SecretDetection]` | Detect secrets in text without instantiating a `SecretsDetector`. | `src/attune/memory/security/secrets_detector.py` |
| `resolve_backend` | `backend: SearchableMemoryBackend \| None = None` | `SearchableMemoryBackend \| None` | Return a searchable backend, or `None` if none is available. | `src/attune/memory/session_stash.py` |
| `backend_status` | — | `dict` | Report which backend recall resolves to, for health surfacing. | `src/attune/memory/session_stash.py` |
| `stash_entry` | `entry: SessionStashEntry, backend: SearchableMemoryBackend \| None = None` | `bool` | Write a finding to the searchable recall tier after the PII gate. | `src/attune/memory/session_stash.py` |
| `recall_entries` | `query: str, top_k: int = 5, cwd: str \| None = None, backend: SearchableMemoryBackend \| None = None` | `list[dict[str, Any]]` | Semantic recall over stashed findings; returns an empty list when unavailable. | `src/attune/memory/session_stash.py` |
| `recent_entries` | `top_k: int = 5, cwd: str \| None = None, backend: SearchableMemoryBackend \| None = None` | `list[dict[str, Any]]` | Query-less recall of the most-recent findings, for use at session start. | `src/attune/memory/session_stash.py` |

### Raises

#### `get_railway_redis`

| Raises | Message |
|--------|---------|
| `OSError` | `'REDIS_URL not found. Make sure Redis is added to your Railway project.\nRun: railway add --database redis\nFor external access, use REDIS_PUBLIC_URL'` |

## Constants

### Cross-session Redis keys

| Constant | Type | Value |
|---------|------|-------|
| `CHANNEL_SESSIONS` | `str` | `'empathy:sessions'` |
| `KEY_ACTIVE_AGENTS` | `str` | `'empathy:active_agents'` |
| `KEY_SERVICE_LOCK` | `str` | `'empathy:service_lock'` |
| `KEY_SERVICE_HEARTBEAT` | `str` | `'empathy:service_heartbeat'` |

### CLAUDE.md delimiters

| Constant | Type | Value |
|---------|------|-------|
| `_CLAUDE_MD_START` | `str` | `'<!-- attune-lessons-start -->'` |
| `_CLAUDE_MD_END` | `str` | `'<!-- attune-lessons-end -->'` |

### Classification keywords

These lists drive auto-classification in `classify_pattern`. A pattern whose content matches keywords from one of these constants is assigned the corresponding classification level.

| Constant | Members |
|---------|---------|
| `HEALTHCARE_KEYWORDS` | `'patient'`, `'medical'`, `'diagnosis'`, `'treatment'`, `'healthcare'`, `'clinical'`, `'hipaa'`, `'phi'`, `'medical record'`, `'prescription'` |
| `FINANCIAL_KEYWORDS` | `'financial'`, `'payment'`, `'credit card'`, `'banking'`, `'transaction'`, `'pci dss'`, `'payment card'` |
| `PROPRIETARY_KEYWORDS` | `'proprietary'`, `'confidential'`, `'internal'`, `'trade secret'`, `'company confidential'`, `'restricted'` |
| `SENSITIVE_PATTERN_TYPES` | `'clinical_protocol'`, `'medical_guideline'`, `'patient_workflow'`, `'financial_procedure'` |
| `INTERNAL_PATTERN_TYPES` | `'architecture'`, `'business_logic'`, `'company_process'` |

## Source files

- `src/attune/memory/**`

## Tags

`memory`, `storage`
