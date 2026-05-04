---
type: reference
feature: memory
depth: reference
generated_at: 2026-05-04T02:32:06.087576+00:00
source_hash: c45e8890bff96a3bad01adc0d5e2914aa9058b01f5de8c8a1985c9b6fe4a7f0f
status: generated
---

# Memory reference

Store, retrieve, and manage persistent and session memory across conversations.

## Classes

### Storage backends

| Class | Description |
|-------|-------------|
| `MemoryBackend` | Protocol for short-term memory backends |
| `SearchableMemoryBackend` | Extended protocol for backends with semantic search |
| `RedisShortTermMemory` | Facade composing all short-term memory operations |
| `LongTermMemory` | Simplified long-term persistent storage interface |
| `MemDocsStorage` | Mock/Simple MemDocs storage backend |

### Memory loaders and configuration

| Class | Description |
|-------|-------------|
| `ClaudeMemoryConfig` | Configuration for Claude memory integration |
| `MemoryFile` | Represents a loaded CLAUDE.md memory file |
| `ClaudeMemoryLoader` | Loads and manages Claude Code memory files (CLAUDE.md) |
| `MemoryConfig` | Configuration for unified memory system |
| `UnifiedMemory` | Unified interface for short-term and long-term memory |

### Control panel and management

| Class | Description |
|-------|-------------|
| `ControlPanelConfig` | Configuration for control panel |
| `MemoryControlPanel` | Enterprise control panel for Empathy memory management |
| `MemoryAPIHandler` | HTTP request handler for Memory Control Panel API |
| `MemoryStats` | Statistics for memory system |

### Session management

| Class | Description |
|-------|-------------|
| `FileSessionMemory` | File-based session memory with persistence |
| `FileSessionConfig` | Configuration for file-based session memory |
| `SessionInfo` | Information about an active session |
| `SessionState` | Complete state of a session |
| `CrossSessionCoordinator` | Coordinator for cross-session agent communication |

### Security and classification

| Class | Description |
|-------|-------------|
| `Classification` | Three-tier classification system for MemDocs patterns |
| `ClassificationRules` | Security rules for each classification level |
| `PatternMetadata` | Metadata for stored MemDocs patterns |
| `SecurePattern` | Represents a securely stored pattern |
| `PIIScrubber` | Comprehensive PII detection and scrubbing system |
| `SecretsDetector` | Detects secrets in text content using pattern matching and entropy analysis |
| `EncryptionManager` | Manages encryption/decryption for SENSITIVE patterns |

### Data classes

#### `ClaudeMemoryConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `False` | Enable Claude memory integration |
| `load_enterprise` | `bool` | `True` | Load enterprise-level memory |
| `load_user` | `bool` | `True` | Load user-specific memory |
| `load_project` | `bool` | `True` | Load project-specific memory |
| `enterprise_memory_path` | `str \| None` | `None` | Path to enterprise memory files |
| `project_root` | `str \| None` | `None` | Root directory for project memory |
| `max_import_depth` | `int` | `5` | Maximum depth for importing memory files |
| `max_file_size_bytes` | `int` | `1000000` | Maximum size for memory files |
| `validate_files` | `bool` | `True` | Validate memory files on load |

#### `MemoryFile`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `level` | `str` | | Memory level (enterprise/user/project) |
| `path` | `str` | | File system path to memory file |
| `content` | `str` | | Content of the memory file |
| `imports` | `list[str]` | `[]` | List of imported memory files |
| `load_order` | `int` | `0` | Order in which file was loaded |

#### `ControlPanelConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `redis_host` | `str` | `'localhost'` | Redis server hostname |
| `redis_port` | `int` | `6379` | Redis server port |
| `storage_dir` | `str` | `'./memdocs_storage'` | Directory for storage files |
| `audit_dir` | `str` | `'./logs'` | Directory for audit logs |
| `auto_start_redis` | `bool` | `True` | Automatically start Redis if needed |

#### `FileSessionConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `storage_dir` | `str` | | Directory for session storage files |
| `auto_save` | `bool` | | Automatically save session state |
| `compression` | `bool` | | Enable compression for session data |

## Functions

### Redis utilities

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `is_redis_available` | | `bool` | Check if Redis subsystem is available without importing it |
| `get_redis_memory` | `url: str \| None = None`, `use_mock: bool \| None = None` | `RedisShortTermMemory` | Create a RedisShortTermMemory instance with environment-based config |
| `check_redis_connection` | | `dict` | Check Redis connection and return status |
| `get_railway_redis` | | `RedisShortTermMemory` | Get Redis configured for Railway deployment |
| `parse_redis_url` | `url: str` | `dict` | Parse Redis URL into connection parameters |
| `get_redis_config` | | `dict` | Get Redis configuration from environment variables (legacy dict API) |

#### `get_railway_redis` raises

| Exception | Message |
|-----------|---------|
| `OSError` | `'REDIS_URL not found. Make sure Redis is added to your Railway project.\nRun: railway add --database redis\nFor external access, use REDIS_PUBLIC_URL'` |

### Memory management

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `create_default_project_memory` | `project_root: str`, `framework: str = 'empathy'` | | Create a default .claude/CLAUDE.md file for a project |
| `get_file_session_memory` | | `FileSessionMemory` | Create a file-based session memory instance |
| `classify_pattern` | | | Auto-classify pattern based on content and type |
| `check_access` | | | Check if user has access to pattern based on classification |

### Control panel

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `run_api_server` | `panel: MemoryControlPanel`, `host: str = 'localhost'`, `port: int = 8765`, `api_key: str \| None = None`, `enable_rate_limit: bool = True`, `rate_limit_requests: int = 100`, `rate_limit_window: int = 60`, `ssl_certfile: str \| None = None`, `ssl_keyfile: str \| None = None`, `allowed_origins: list[str] \| None = None` | | Run the Memory API server with security features |
| `print_status` | `panel: MemoryControlPanel` | | Print status in a formatted way |
| `print_stats` | `panel: MemoryControlPanel` | | Print statistics in a formatted way |

### Security

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `detect_secrets` | | | Convenience function to detect secrets without creating a detector instance |

### Cross-session coordination

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `generate_agent_id` | | | Generate a unique agent ID |
| `check_redis_cross_session_support` | | | Check if Redis supports cross-session communication |
| `get_or_start_service` | | | Get existing service or start a new one |

### Redis lifecycle

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `ensure_redis` | | | Ensure Redis is available, starting it if necessary |
| `stop_redis` | | | Stop Redis if we started it |
| `get_redis_or_mock` | | | Get a Redis connection, starting Redis if needed, or return mock |
| `auto_detect_redis` | | | Convenience function for auto-detecting Redis |

## Constants

### Cross-session keys

| Constant | Value | Description |
|----------|-------|-------------|
| `CHANNEL_SESSIONS` | `'empathy:sessions'` | Redis channel for session coordination |
| `KEY_ACTIVE_AGENTS` | `'empathy:active_agents'` | Redis key for active agent registry |
| `KEY_SERVICE_LOCK` | `'empathy:service_lock'` | Redis key for service coordination lock |
| `KEY_SERVICE_HEARTBEAT` | `'empathy:service_heartbeat'` | Redis key for service heartbeat |

### Security keywords

| Constant | Members | Description |
|----------|---------|-------------|
| `HEALTHCARE_KEYWORDS` | `'patient'`, `'medical'`, `'diagnosis'`, `'treatment'`, `'healthcare'`, `'clinical'`, `'hipaa'`, `'phi'`, `'medical record'`, `'prescription'` | Keywords that trigger healthcare classification |
| `FINANCIAL_KEYWORDS` | `'financial'`, `'payment'`, `'credit card'`, `'banking'`, `'transaction'`, `'pci dss'`, `'payment card'` | Keywords that trigger financial classification |
| `PROPRIETARY_KEYWORDS` | `'proprietary'`, `'confidential'`, `'internal'`, `'trade secret'`, `'company confidential'`, `'restricted'` | Keywords that trigger proprietary classification |
| `SENSITIVE_PATTERN_TYPES` | `'clinical_protocol'`, `'medical_guideline'`, `'patient_workflow'`, `'financial_procedure'` | Pattern types requiring sensitive handling |
| `INTERNAL_PATTERN_TYPES` | `'architecture'`, `'business_logic'`, `'company_process'` | Pattern types for internal use only |

### Template markers

| Constant | Value | Description |
|----------|-------|-------------|
| `_CLAUDE_MD_START` | `'<!-- attune-lessons-start -->'` | Start marker for lessons section in CLAUDE.md |
| `_CLAUDE_MD_END` | `'<!-- attune-lessons-end -->'` | End marker for lessons section in CLAUDE.md |
