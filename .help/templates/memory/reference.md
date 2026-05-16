---
type: reference
name: memory-reference
feature: memory
depth: reference
generated_at: 2026-05-16T06:14:13.784755+00:00
source_hash: 54f52a79be1ecfe32e99b4f09f84bda845815a0129b603c252aa4c74c2e1a61c
status: generated
---

# Memory reference

Classes, functions, and constants for storing, retrieving, searching, and securing memory across sessions.

## Classes

| Class | Description |
|-------|-------------|
| `MemoryBackend` | Protocol for short-term memory backends. |
| `SearchableMemoryBackend` | Extended protocol for backends with semantic search. |
| `ClaudeMemoryConfig` | Configuration for Claude memory integration. |
| `MemoryFile` | Represents a loaded CLAUDE.md memory file. |
| `ClaudeMemoryLoader` | Loads and manages Claude Code memory files (CLAUDE.md). |
| `ControlPanelConfig` | Configuration for the control panel. |
| `MemoryControlPanel` | Enterprise control panel for Empathy memory management. |
| `MemoryAPIHandler` | HTTP request handler for the Memory Control Panel API. |
| `RateLimiter` | Simple in-memory rate limiter by IP address. |
| `APIKeyAuth` | Simple API key authentication. |
| `MemoryStats` | Statistics for the memory system. |
| `CrossSessionCoordinator` | Coordinator for cross-session agent communication. |
| `SessionType` | Type of session or agent. |
| `ConflictStrategy` | Strategy for resolving conflicts between agents. |
| `SessionInfo` | Information about an active session. |
| `ConflictResult` | Result of a conflict resolution. |
| `BackgroundService` | Background service daemon for cross-session coordination. |
| `EdgeType` | Types of relationships between nodes. |
| `Edge` | An edge connecting two nodes in the memory graph. |
| `EncryptionManager` | Manages encryption and decryption for SENSITIVE patterns. |
| `FeatureStatus` | Status of an optional feature. |
| `FeatureInfo` | Information about a memory feature. |
| `MemoryFeatures` | Check availability of memory subsystem features. |
| `FileSessionMemory` | File-based session memory with persistence. |
| `FileSessionConfig` | Configuration for file-based session memory. |
| `WorkingEntry` | Entry in working memory. |
| `StagedPatternFile` | Pattern staged for validation (file-based version). |
| `SessionState` | Complete state of a session. |
| `PatternStagingMixin` | Mixin providing pattern staging operations. |
| `PersistenceMixin` | Mixin providing session persistence operations. |
| `MemoryGraph` | Knowledge graph for cross-workflow intelligence. |
| `LessonsManager` | Manages lessons learned from previous sessions. |
| `SecureMemDocsIntegration` | Secure integration between Claude Memory and MemDocs. |
| `PatternOperationsMixin` | Mixin providing pattern list, delete, and statistics operations. |
| `PatternPipelineMixin` | Mixin providing store/retrieve pipeline helpers. |
| `Classification` | Three-tier classification system for MemDocs patterns. |
| `ClassificationRules` | Security rules for each classification level. |
| `PatternMetadata` | Metadata for stored MemDocs patterns. |
| `SecurePattern` | Represents a securely stored pattern. |
| `SecurityError` | Raised when a security policy is violated. |
| `MemoryPermissionError` | Raised when access is denied. |
| `BackendInitMixin` | Mixin providing backend initialization for `UnifiedMemory`. |
| `CapabilitiesMixin` | Mixin providing capability detection and health checks for `UnifiedMemory`. |
| `HandoffAndExportMixin` | Mixin providing session handoff and export capabilities for `UnifiedMemory`. |
| `LifecycleMixin` | Mixin providing lifecycle management for `UnifiedMemory`. |
| `LongTermOperationsMixin` | Mixin providing long-term memory operations for `UnifiedMemory`. |
| `PatternPromotionMixin` | Mixin providing pattern promotion capabilities for `UnifiedMemory`. |
| `ShortTermOperationsMixin` | Mixin providing short-term memory operations for `UnifiedMemory`. |
| `NodeType` | Types of nodes in the memory graph. |
| `Node` | A node in the memory graph. |
| `BugNode` | Specialized node for bugs. |
| `VulnerabilityNode` | Specialized node for security vulnerabilities. |
| `PerformanceNode` | Specialized node for performance issues. |
| `PatternNode` | Specialized node for code patterns. |
| `PersonalMemory` | Store and retrieve personal cross-session memory. |
| `RedisDetectionResult` | Result of Redis auto-detection. |
| `RedisAutoDetector` | Auto-detects Redis availability and manages user preferences. |
| `RedisStartMethod` | Methods for starting Redis, in order of preference. |
| `RedisStatus` | Status of a Redis connection or startup attempt. |
| `AuditLogger` | Comprehensive audit logging for Attune AI. |
| `AuditEvent` | Represents a single audit event. |
| `SecurityViolation` | Represents a security policy violation. |
| `AuditLogMethodsMixin` | Mixin that adds event-specific logging methods. |
| `PIIDetection` | Details about a detected PII instance. |
| `PIIPattern` | Definition of a PII detection pattern. |
| `PIIScrubber` | Comprehensive PII detection and scrubbing system. |
| `AuditQueryMixin` | Mixin that adds query capabilities to `AuditLogger`. |
| `AuditReportMixin` | Mixin that adds reporting capabilities to `AuditLogger`. |
| `SecretsDetector` | Detects secrets in text content using pattern matching and entropy analysis. |
| `SecretType` | Types of secrets that can be detected. |
| `Severity` | Severity levels for secret detections. |
| `SecretDetection` | Metadata about a detected secret. |
| `BaseOperations` | CRUD operations and connection management for short-term memory. |
| `BatchOperations` | Batch operations using Redis pipelines. |
| `CacheManager` | Local LRU cache manager for two-tier caching. |
| `ConflictNegotiation` | Conflict context and resolution operations. |
| `CrossSessionManager` | Cross-session coordination operations. |
| `RedisShortTermMemory` | Facade composing all short-term memory operations. |
| `Pagination` | SCAN-based pagination operations. |
| `PatternStaging` | Pattern staging lifecycle operations. |
| `PubSubManager` | Real-time publish/subscribe operations. |
| `QueueManager` | Redis list operations for task queues. |
| `DataSanitizer` | Handles data sanitization for short-term memory. |
| `SessionManager` | Collaboration session operations. |
| `StreamManager` | Redis Streams operations for audit trails and event logs. |
| `TimelineManager` | Redis sorted set operations for timeline queries. |
| `TransactionManager` | Atomic operations using Redis transactions. |
| `WorkingMemory` | Working memory operations for agent data storage. |
| `LongTermMemory` | Simplified long-term persistent storage interface. |
| `MemDocsStorage` | Mock/simple MemDocs storage backend. |
| `AgentContext` | Compact context package for sub-agent handoff. |
| `ConversationSummaryIndex` | Redis-backed conversation summary with topic indexing. |
| `AccessTier` | Role-based access tiers per EMPATHY_PHILOSOPHY.md. |
| `TTLStrategy` | TTL strategies for different memory types. |
| `RedisConfig` | Enhanced Redis configuration with SSL and retry support. |
| `RedisMetrics` | Metrics for Redis operations. |
| `PaginatedResult` | Result of a paginated query. |
| `TimeWindowQuery` | Query parameters for time-window operations. |
| `AgentCredentials` | Agent identity and access permissions. |
| `StagedPattern` | Pattern awaiting validation. |
| `ConflictContext` | Context for principled negotiation. |
| `Environment` | Deployment environment for storage configuration. |
| `MemoryConfig` | Configuration for the unified memory system. |
| `UnifiedMemory` | Unified interface for short-term and long-term memory. |

### `MemoryBackend` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `stash` | `key: str, value: Any, ttl: int \| None = None, agent_id: str \| None = None` | `bool` | Store a value under the given key. |
| `retrieve` | `key: str, agent_id: str \| None = None` | `Any \| None` | Retrieve a value by key. |
| `delete` | `key: str` | `bool` | Delete the entry for a key. |
| `keys` | `pattern: str = '*'` | `list[str]` | List keys matching a pattern. |
| `is_connected` | — | `bool` | Return whether the backend is connected. |
| `get_stats` | — | `dict` | Return backend statistics. |
| `close` | — | — | Close the backend connection. |
| `supports_realtime` | — | `bool` | Return whether the backend supports real-time operations. |
| `supports_distributed` | — | `bool` | Return whether the backend supports distributed access. |

### `SearchableMemoryBackend` methods

`SearchableMemoryBackend` extends `MemoryBackend` with the following additional methods.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `search` | `query: str, limit: int = 10, **filters: Any` | `list[dict]` | Search memory using a query string with optional filters. |
| `promote` | `session_id: str \| None = None` | `bool` | Promote staged patterns to long-term memory. |

### `ClaudeMemoryConfig` fields

`ClaudeMemoryConfig` is a dataclass. Configuration for Claude memory integration.

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

### `MemoryFile` fields

`MemoryFile` is a dataclass. Represents a loaded CLAUDE.md memory file.

| Field | Type | Default |
|-------|------|---------|
| `level` | `str` | — |
| `path` | `str` | — |
| `content` | `str` | — |
| `imports` | `list[str]` | `field(default_factory=list)` |
| `load_order` | `int` | `0` |

### `ClaudeMemoryLoader` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `config: ClaudeMemoryConfig \| None = None` | — | Initialize the loader with an optional configuration. |
| `load_all_memory` | `project_root: str \| None = None` | `str` | Load all CLAUDE.md memory files and return combined content. |
| `clear_cache` | — | — | Clear the loaded file cache. |
| `get_loaded_files` | — | `list[str]` | Return the paths of all currently loaded files. |

### `ControlPanelConfig` fields

`ControlPanelConfig` is a dataclass. Configuration for the control panel.

| Field | Type | Default |
|-------|------|---------|
| `redis_host` | `str` | `'localhost'` |
| `redis_port` | `int` | `6379` |
| `storage_dir` | `str` | `'./memdocs_storage'` |
| `audit_dir` | `str` | `'./logs'` |
| `auto_start_redis` | `bool` | `True` |

### `MemoryControlPanel` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `config: ControlPanelConfig \| None = None` | — | Initialize the control panel with an optional configuration. |
| `status` | — | `dict[str, Any]` | Return current system status. |
| `start_redis` | `verbose: bool = True` | `RedisStatus` | Start the Redis backend. |
| `stop_redis` | — | `bool` | Stop the Redis backend. |
| `get_statistics` | — | `MemoryStats` | Return memory system statistics. |
| `list_patterns` | `classification: str \| None = None, limit: int = 100` | `list[dict[str, Any]]` | List stored patterns, optionally filtered by classification. |
| `delete_pattern` | `pattern_id: str, user_id: str = 'admin@system'` | `bool` | Delete a pattern by ID. |
| `clear_short_term` | `agent_id: str = 'admin'` | `int` | Clear short-term memory for an agent and return the count of cleared entries. |
| `export_patterns` | `output_path: str, classification: str \| None = None` | `int` | Export patterns to a file and return the count exported. |
| `health_check` | — | `dict[str, Any]` | Run a health check and return the results. |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `is_redis_available` | — | `bool` | Check whether the Redis subsystem is available without importing it. |
| `create_default_project_memory` | `project_root: str, framework: str = 'empathy'` | — | Create a default `.claude/CLAUDE.md` file for a project. |
| `parse_redis_url` | `url: str` | `dict` | Parse a Redis URL into connection parameters. |
| `get_redis_config` | — | `dict` | Get Redis configuration from environment variables (legacy dict API). |
| `get_redis_memory` | `url: str \| None = None, use_mock: bool \| None = None` | `RedisShortTermMemory` | Create a `RedisShortTermMemory` instance using environment-based config. |
| `check_redis_connection` | — | `dict` | Check the Redis connection and return status. |
| `get_railway_redis` | — | `RedisShortTermMemory` | Get a Redis instance configured for Railway deployment. |
| `run_api_server` | `panel: MemoryControlPanel, host: str = 'localhost', port: int = 8765, api_key: str \| None = None, enable_rate_limit: bool = True, rate_limit_requests: int = 100, rate_limit_window: int = 60, ssl_certfile: str \| None = None, ssl_keyfile: str \| None = None, allowed_origins: list[str] \| None = None` | — | Run the Memory API server with security features. |
| `print_status` | `panel: MemoryControlPanel` | — | Print control panel status in a formatted way. |
| `print_stats` | `panel: MemoryControlPanel` | — | Print memory statistics in a formatted way. |
| `print_health` | `panel: MemoryControlPanel` | — | Print a health check report in a formatted way. |
| `main` | — | — | CLI entry point. |
| `resolve_by_priority` | `agent_id: str, access_tier: AccessTier, session_info: SessionInfo, resource_key: str, other_session: SessionInfo \| None` | `Con
