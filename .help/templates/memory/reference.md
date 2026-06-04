---
type: reference
name: memory-reference
feature: memory
depth: reference
generated_at: 2026-06-04T23:45:26.848192+00:00
source_hash: c6803543f79e6bd38c2393239d6731920690afcab986165d0ce938b8ba0d5c25
status: generated
---

# Memory reference

Store, retrieve, search, and secure persistent memory across sessions and agents.

## Classes

The table below lists every public class in `src/attune/memory/`. Protocol classes define the interfaces that backends must implement. Dataclass fields are expanded in the sections that follow.

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
| `RateLimiter` | In-memory rate limiter keyed by IP address. | `src/attune/memory/control_panel_support.py` |
| `APIKeyAuth` | Simple API key authentication. | `src/attune/memory/control_panel_support.py` |
| `MemoryStats` | Statistics for the memory system. | `src/attune/memory/control_panel_support.py` |
| `CrossSessionCoordinator` | Coordinator for cross-session agent communication. | `src/attune/memory/cross_session/coordinator.py` |
| `SessionType` | Type of session or agent. | `src/attune/memory/cross_session/models.py` |
| `ConflictStrategy` | Strategy for resolving conflicts between agents. | `src/attune/memory/cross_session/models.py` |
| `SessionInfo` | Information about an active session. | `src/attune/memory/cross_session/models.py` |
| `ConflictResult` | Result of a conflict resolution. | `src/attune/memory/cross_session/models.py` |
| `BackgroundService` | Background service daemon for cross-session coordination. | `src/attune/memory/cross_session/service.py` |
| `EdgeType` | Types of relationships between nodes. | `src/attune/memory/edges.py` |
| `Edge` | An edge connecting two nodes in the memory graph. | `src/attune/memory/edges.py` |
| `EncryptionManager` | Manages encryption and decryption for SENSITIVE patterns. | `src/attune/memory/encryption.py` |
| `FeatureStatus` | Status of an optional feature. | `src/attune/memory/features.py` |
| `FeatureInfo` | Information about a memory feature. | `src/attune/memory/features.py` |
| `MemoryFeatures` | Checks availability of memory subsystem features. | `src/attune/memory/features.py` |
| `FileSessionMemory` | File-based session memory with persistence. | `src/attune/memory/file_session.py` |
| `FileSessionConfig` | Configuration for file-based session memory. | `src/attune/memory/file_session_models.py` |
| `WorkingEntry` | Entry in working memory. | `src/attune/memory/file_session_models.py` |
| `StagedPatternFile` | Pattern staged for validation (file-based version). | `src/attune/memory/file_session_models.py` |
| `SessionState` | Complete state of a session. | `src/attune/memory/file_session_models.py` |
| `PatternStagingMixin` | Mixin providing pattern staging operations. | `src/attune/memory/file_session_patterns.py` |
| `PersistenceMixin` | Mixin providing session persistence operations. | `src/attune/memory/file_session_persistence.py` |
| `FileStashBackend` | Searchable, zero-infra session stash backed by a local JSONL file. | `src/attune/memory/file_stash.py` |
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
| `BackendInitMixin` | Mixin providing backend initialization for `UnifiedMemory`. | `src/attune/memory/mixins/backend_init_mixin.py` |
| `CapabilitiesMixin` | Mixin providing capability detection and health checks for `UnifiedMemory`. | `src/attune/memory/mixins/capabilities_mixin.py` |
| `HandoffAndExportMixin` | Mixin providing session handoff and export capabilities for `UnifiedMemory`. | `src/attune/memory/mixins/handoff_mixin.py` |
| `LifecycleMixin` | Mixin providing lifecycle management for `UnifiedMemory`. | `src/attune/memory/mixins/lifecycle_mixin.py` |
| `LongTermOperationsMixin` | Mixin providing long-term memory operations for `UnifiedMemory`. | `src/attune/memory/mixins/long_term_mixin.py` |
| `PatternPromotionMixin` | Mixin providing pattern promotion capabilities for `UnifiedMemory`. | `src/attune/memory/mixins/promotion_mixin.py` |
| `ShortTermOperationsMixin` | Mixin providing short-term memory operations for `UnifiedMemory`. | `src/attune/memory/mixins/short_term_mixin.py` |
| `NodeType` | Types of nodes in the memory graph. | `src/attune/memory/nodes.py` |
| `Node` | A node in the memory graph. | `src/attune/memory/nodes.py` |
| `BugNode` | Specialized node for bugs. | `src/attune/memory/nodes.py` |
| `VulnerabilityNode` | Specialized node for security vulnerabilities. | `src/attune/memory/nodes.py` |
| `PerformanceNode` | Specialized node for performance issues. | `src/attune/memory/nodes.py` |
| `PatternNode` | Specialized node for code patterns. | `src/attune/memory/nodes.py` |
| `PersonalMemory` | Store and retrieve personal cross-session memory. | `src/attune/memory/personal.py` |
| `RedisDetectionResult` | Result of Redis auto-detection. | `src/attune/memory/redis_auto_detect.py` |
| `RedisAutoDetector` | Auto-detects Redis availability and manages user preferences. | `src/attune/memory/redis_auto_detect.py` |
| `RedisStartMethod` | Methods for starting Redis, in order of preference. | `src/attune/memory/redis_bootstrap.py` |
| `RedisStatus` | Status of a Redis connection or startup attempt. | `src/attune/memory/redis_bootstrap.py` |
| `AuditLogger` | Comprehensive audit logging for Attune AI. | `src/attune/memory/security/audit_logger.py` |
| `AuditEvent` | Represents a single audit event. | `src/attune/memory/security/events.py` |
| `SecurityViolation` | Represents a security policy violation. | `src/attune/memory/security/events.py` |
| `AuditLogMethodsMixin` | Mixin that adds event-specific logging methods. | `src/attune/memory/security/log_methods.py` |
| `PIIDetection` | Details about a detected PII instance. | `src/attune/memory/security/pii_scrubber.py` |
| `PIIPattern` | Definition of a PII detection pattern. | `src/attune/memory/security/pii_scrubber.py` |
| `PIIScrubber` | Comprehensive PII detection and scrubbing system. | `src/attune/memory/security/pii_scrubber.py` |
| `AuditQueryMixin` | Mixin that adds query capabilities to `AuditLogger`. | `src/attune/memory/security/query.py` |
| `AuditReportMixin` | Mixin that adds reporting capabilities to `AuditLogger`. | `src/attune/memory/security/reports.py` |
| `SecretsDetector` | Detects secrets in text using pattern matching and entropy analysis. | `src/attune/memory/security/secrets_detector.py` |
| `SecretType` | Types of secrets that can be detected. | `src/attune/memory/security/secrets_types.py` |
| `Severity` | Severity levels for secret detections. | `src/attune/memory/security/secrets_types.py` |
| `SecretDetection` | Metadata about a detected secret. | `src/attune/memory/security/secrets_types.py` |
| `SessionStashEntry` | A single raw cross-session finding awaiting recall or promotion. | `src/attune/memory/session_stash.py` |
| `BaseOperations` | Core CRUD operations and connection management. | `src/attune/memory/short_term/base.py` |
| `BatchOperations` | Batch operations using Redis pipelines. | `src/attune/memory/short_term/batch.py` |
| `CacheManager` | Local LRU cache manager for two-tier caching. | `src/attune/memory/short_term/caching.py` |
| `ConflictNegotiation` | Conflict context and resolution operations. | `src/attune/memory/short_term/conflicts.py` |
| `CrossSessionManager` | Cross-session coordination operations. | `src/attune/memory/short_term/cross_session.py` |
| `RedisShortTermMemory` | Facade composing all short-term memory operations. | `src/attune/memory/short_term/facade.py` |
| `Pagination` | SCAN-based pagination operations. | `src/attune/memory/short_term/pagination.py` |
| `PatternStaging` | Pattern staging lifecycle operations. | `src/attune/memory/short_term/patterns.py` |
| `PubSubManager` | Real-time publish/subscribe operations. | `src/attune/memory/short_term/pubsub.py` |
| `QueueManager` | Redis list operations for task queues. | `src/attune/memory/short_term/queues.py` |
| `DataSanitizer` | Handles data sanitization for short-term memory. | `src/attune/memory/short_term/security.py` |
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
| `SecurityError` | Raised when a security policy is violated (for example, secrets detected in data). | `src/attune/memory/types.py` |
| `Environment` | Deployment environment for storage configuration. | `src/attune/memory/unified.py` |
| `MemoryConfig` | Configuration for the unified memory system. | `src/attune/memory/unified.py` |
| `UnifiedMemory` | Unified interface for short-term and long-term memory. | `src/attune/memory/unified.py` |

## Dataclass fields

### `ClaudeMemoryConfig`

Configuration for Claude memory integration.

| Field | Type | Default |
|-------|------|---------|
| `enabled` | `bool` | `False` |
| `load_enterprise` | `bool` | `True` |
| `load_user` | `bool` | `True` |
| `load_project` | `bool` | `True` |
| `enterprise_memory_path` | `str \| None` | `None` |
| `project_root` | `str \| None` | `None` |
|
