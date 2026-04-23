---
type: reference
feature: memory
depth: reference
generated_at: 2026-04-23T03:31:10.383354+00:00
source_hash: 65cd08d1432d00333db89709ddcd7b9eb6a2277e6649a322b27cb5880d2058a3
status: generated
---

# Memory reference

Store, retrieve, and search persistent data across Claude sessions with unified short-term and long-term storage.

## Core classes

| Class | Description |
|-------|-------------|
| `UnifiedMemory` | Unified interface for short-term and long-term memory |
| `RedisShortTermMemory` | Redis-backed short-term memory with cross-session coordination |
| `FileSessionMemory` | File-based session memory with persistence |
| `LongTermMemory` | Simplified long-term persistent storage interface |
| `PersonalMemory` | Store and retrieve personal cross-session memory |

## Configuration classes

| Class | Parameters | Description |
|-------|------------|-------------|
| `MemoryConfig` | `redis_url: str \| None = None`, `redis_config: RedisConfig \| None = None`, `long_term_storage: str = './memdocs_storage'`, `claude_memory_enabled: bool = True`, `environment: Environment = Environment.DEVELOPMENT`, `encryption_enabled: bool = False` | Configuration for unified memory system |
| `ClaudeMemoryConfig` | `enabled: bool = False`, `load_enterprise: bool = True`, `load_user: bool = True`, `load_project: bool = True`, `enterprise_memory_path: str \| None = None`, `project_root: str \| None = None`, `max_import_depth: int = 5`, `max_file_size_bytes: int = 1000000`, `validate_files: bool = True` | Configuration for Claude memory integration |
| `FileSessionConfig` | `storage_dir: str = './session_memory'`, `max_size: int = 1000000`, `enable_compression: bool = True` | Configuration for file-based session memory |
| `RedisConfig` | `host: str = 'localhost'`, `port: int = 6379`, `db: int = 0`, `password: str \| None = None`, `ssl: bool = False`, `ssl_cert_reqs: str = 'required'`, `ssl_ca_certs: str \| None = None`, `max_connections: int = 100`, `retry_on_timeout: bool = True` | Enhanced Redis configuration with SSL and retry support |

## Backend protocols

| Class | Methods | Returns |
|-------|---------|---------|
| `MemoryBackend` | `stash(key: str, value: Any, ttl: int \| None = None, agent_id: str \| None = None)` | `bool` |
|  | `retrieve(key: str, agent_id: str \| None = None)` | `Any \| None` |
|  | `delete(key: str)` | `bool` |
|  | `keys(pattern: str = '*')` | `list[str]` |
|  | `is_connected()` | `bool` |
|  | `get_stats()` | `dict` |
|  | `close()` | `None` |
|  | `supports_realtime()` | `bool` |
|  | `supports_distributed()` | `bool` |
| `SearchableMemoryBackend` | `search(query: str, limit: int = 10, **filters: Any)` | `list[dict]` |
|  | `promote(session_id: str \| None = None)` | `bool` |

## Security and classification

| Class | Fields | Description |
|-------|--------|-------------|
| `Classification` | PUBLIC, INTERNAL, SENSITIVE | Three-tier classification system for MemDocs patterns |
| `ClassificationRules` | `encryption_required: bool`, `audit_required: bool`, `access_tiers: list[AccessTier]` | Security rules for each classification level |
| `PatternMetadata` | `id: str`, `pattern_type: str`, `content_hash: str`, `classification: Classification`, `created_at: datetime`, `last_accessed: datetime \| None`, `access_count: int`, `tags: list[str]`, `user_id: str` | Metadata for stored MemDocs patterns |
| `SecurePattern` | `metadata: PatternMetadata`, `content: str`, `is_encrypted: bool` | Represents a securely stored pattern |
| `PIIScrubber` | Comprehensive PII detection and scrubbing system |  |
| `SecretsDetector` | Detects secrets in text content using pattern matching and entropy analysis |  |

## Cross-session coordination

| Class | Fields | Description |
|-------|--------|-------------|
| `CrossSessionCoordinator` | Coordinator for cross-session agent communication |  |
| `SessionType` | INTERACTIVE, BATCH, SYSTEM | Type of session/agent |
| `ConflictStrategy` | PRIORITY, FIRST_WRITE, LAST_WRITE, NEGOTIATE | Strategy for resolving conflicts between agents |
| `SessionInfo` | `session_id: str`, `agent_id: str`, `session_type: SessionType`, `started_at: datetime`, `last_heartbeat: datetime`, `access_tier: AccessTier` | Information about an active session |
| `ConflictResult` | `resolved: bool`, `winner: str \| None`, `strategy_used: ConflictStrategy`, `resolution_data: dict` | Result of a conflict resolution |

## Memory graph

| Class | Description |
|-------|-------------|
| `MemoryGraph` | Knowledge graph for cross-workflow intelligence |
| `NodeType` | Types of nodes in the memory graph |
| `Node` | A node in the memory graph |
| `BugNode` | Specialized node for bugs |
| `VulnerabilityNode` | Specialized node for security vulnerabilities |
| `PerformanceNode` | Specialized node for performance issues |
| `PatternNode` | Specialized node for code patterns |
| `EdgeType` | Types of relationships between nodes |
| `Edge` | An edge connecting two nodes in the memory graph |

## Factory functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_redis_memory` | `url: str \| None = None`, `use_mock: bool \| None = None` | `RedisShortTermMemory` | Create a RedisShortTermMemory instance with environment-based config |
| `get_file_session_memory` |  | `FileSessionMemory` | Create a file-based session memory instance |
| `get_railway_redis` |  | `RedisShortTermMemory` | Get Redis configured for Railway deployment |

## Utility functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `is_redis_available` |  | `bool` | Check if Redis subsystem is available without importing it |
| `check_redis_connection` |  | `dict` | Check Redis connection and return status |
| `parse_redis_url` | `url: str` | `dict` | Parse Redis URL into connection parameters |
| `create_default_project_memory` | `project_root: str`, `framework: str = 'empathy'` | `None` | Create a default .claude/CLAUDE.md file for a project |
| `classify_pattern` | Pattern content and metadata | `Classification` | Auto-classify pattern based on content and type |
| `check_access` | User credentials and pattern classification | `bool` | Check if user has access to pattern based on classification |
| `detect_secrets` | `text: str` | `list[SecretDetection]` | Convenience function to detect secrets without creating a detector instance |

## Constants

| Constant | Values | Description |
|----------|--------|-------------|
| `HEALTHCARE_KEYWORDS` | `patient`, `medical`, `diagnosis`, `treatment`, `healthcare`, `clinical`, `hipaa`, `phi`, `medical record`, `prescription` | Keywords that trigger healthcare classification |
| `FINANCIAL_KEYWORDS` | `financial`, `payment`, `credit card`, `banking`, `transaction`, `pci dss`, `payment card` | Keywords that trigger financial classification |
| `PROPRIETARY_KEYWORDS` | `proprietary`, `confidential`, `internal`, `trade secret`, `company confidential`, `restricted` | Keywords that trigger proprietary classification |
| `SENSITIVE_PATTERN_TYPES` | `clinical_protocol`, `medical_guideline`, `patient_workflow`, `financial_procedure` | Pattern types that default to SENSITIVE classification |
| `INTERNAL_PATTERN_TYPES` | `architecture`, `business_logic`, `company_process` | Pattern types that default to INTERNAL classification |
