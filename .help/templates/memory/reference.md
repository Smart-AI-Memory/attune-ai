---
type: reference
feature: memory
depth: reference
generated_at: 2026-04-14T15:05:02.992534+00:00
source_hash: becc5608c1ce3b9583965f538dce42193f013b114a01d1fbfa3234d4228db706
status: generated
---

# Memory reference

## Core protocols

| Class | Description |
|-------|-------------|
| `MemoryBackend` | Protocol for short-term memory backends |
| `SearchableMemoryBackend` | Extended protocol for backends with semantic search |

### MemoryBackend methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `stash` | `key: str, value: Any, ttl: int \| None = None, agent_id: str \| None = None` | `bool` | Store value with optional TTL and agent scope |
| `retrieve` | `key: str, agent_id: str \| None = None` | `Any \| None` | Retrieve value by key and optional agent scope |
| `delete` | `key: str` | `bool` | Delete key from storage |
| `keys` | `pattern: str = '*'` | `list[str]` | List keys matching pattern |
| `is_connected` | | `bool` | Check if backend is connected |
| `get_stats` | | `dict` | Get backend statistics |
| `close` | | `None` | Close backend connection |
| `supports_realtime` | | `bool` | Check if backend supports real-time features |
| `supports_distributed` | | `bool` | Check if backend supports distributed features |

### SearchableMemoryBackend methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `search` | `query: str, limit: int = 10, **filters: Any` | `list[dict]` | Perform semantic search with filters |
| `promote` | `session_id: str \| None = None` | `bool` | Promote session data to long-term storage |

## Configuration dataclasses

### ClaudeMemoryConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `False` | Enable Claude memory integration |
| `load_enterprise` | `bool` | `True` | Load enterprise-level memory files |
| `load_user` | `bool` | `True` | Load user-level memory files |
| `load_project` | `bool` | `True` | Load project-level memory files |
| `enterprise_memory_path` | `str \| None` | `None` | Path to enterprise memory files |
| `project_root` | `str \| None` | `None` | Project root directory |
| `max_import_depth` | `int` | `5` | Maximum import depth for memory files |
| `max_file_size_bytes` | `int` | `1000000` | Maximum file size in bytes |
| `validate_files` | `bool` | `True` | Validate memory files on load |

### MemoryFile

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `level` | `str` | | Memory file level (enterprise, project, user) |
| `path` | `str` | | File path |
| `content` | `str` | | File content |
| `imports` | `list[str]` | `[]` | List of imported files |
| `load_order` | `int` | `0` | Loading order priority |

### ControlPanelConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `redis_host` | `str` | `'localhost'` | Redis server hostname |
| `redis_port` | `int` | `6379` | Redis server port |
| `storage_dir` | `str` | `'./memdocs_storage'` | Storage directory path |
| `audit_dir` | `str` | `'./logs'` | Audit logs directory |
| `auto_start_redis` | `bool` | `True` | Automatically start Redis if needed |

## Memory management classes

### ClaudeMemoryLoader

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `config: ClaudeMemoryConfig \| None = None` | | Initialize loader with configuration |
| `load_all_memory` | `project_root: str \| None = None` | `str` | Load all memory files and return combined content |
| `clear_cache` | | `None` | Clear internal cache |
| `get_loaded_files` | | `list[str]` | Get list of loaded file paths |

### MemoryControlPanel

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `config: ControlPanelConfig \| None = None` | | Initialize control panel |
| `status` | | `dict[str, Any]` | Get system status |
| `start_redis` | `verbose: bool = True` | `RedisStatus` | Start Redis server |
| `stop_redis` | | `bool` | Stop Redis server |
| `get_statistics` | | `MemoryStats` | Get memory statistics |
| `list_patterns` | `classification: str \| None = None, limit: int = 100` | `list[dict[str, Any]]` | List stored patterns |
| `delete_pattern` | `pattern_id: str, user_id: str = 'admin@system'` | `bool` | Delete specific pattern |
| `clear_short_term` | `agent_id: str = 'admin'` | `int` | Clear short-term memory for agent |
| `export_patterns` | `output_path: str, classification: str \| None = None` | `int` | Export patterns to file |
| `health_check` | | `dict[str, Any]` | Perform health check |

## Security classes

### RateLimiter

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `window_seconds: int = 60, max_requests: int = 100` | | Initialize rate limiter |
| `is_allowed` | `client_ip: str` | `bool` | Check if request is allowed |
| `get_remaining` | `client_ip: str` | `int` | Get remaining requests for IP |

### APIKeyAuth

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `api_key: str \| None = None` | | Initialize API key authentication |
| `is_valid` | `provided_key: str \| None` | `bool` | Validate provided API key |

## Utility functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `is_redis_available` | | `bool` | Check if Redis subsystem is available |
| `create_default_project_memory` | `project_root: str, framework: str = 'empathy'` | `None` | Create default .claude/CLAUDE.md file |
| `parse_redis_url` | `url: str` | `dict` | Parse Redis URL into connection parameters |
| `get_redis_config` | | `dict` | Get Redis configuration from environment |
| `get_redis_memory` | `url: str \| None = None, use_mock: bool \| None = None` | `RedisShortTermMemory` | Create Redis memory instance |
| `check_redis_connection` | | `dict` | Check Redis connection status |
| `get_railway_redis` | | `RedisShortTermMemory` | Get Redis configured for Railway deployment |

### get_railway_redis exceptions

| Exception | Message |
|-----------|---------|
| `OSError` | `'REDIS_URL not found. Make sure Redis is added to your Railway project.\nRun: railway add --database redis\nFor external access, use REDIS_PUBLIC_URL'` |

## API server functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `run_api_server` | `panel: MemoryControlPanel, host: str = 'localhost', port: int = 8765, api_key: str \| None = None, enable_rate_limit: bool = True, rate_limit_requests: int = 100, rate_limit_window: int = 60, ssl_certfile: str \| None = None, ssl_keyfile: str \| None = None, allowed_origins: list[str] \| None = None` | `None` | Run Memory API server with security features |
| `print_status` | `panel: MemoryControlPanel` | `None` | Print formatted status output |
| `print_stats` | `panel: MemoryControlPanel` | `None` | Print formatted statistics output |

## Constants

### Channel and key names

| Constant | Value | Description |
|----------|-------|-------------|
| `CHANNEL_SESSIONS` | `'empathy:sessions'` | Redis channel for session events |
| `KEY_ACTIVE_AGENTS` | `'empathy:active_agents'` | Redis key for active agents list |
| `KEY_SERVICE_LOCK` | `'empathy:service_lock'` | Redis key for service coordination lock |
| `KEY_SERVICE_HEARTBEAT` | `'empathy:service_heartbeat'` | Redis key for service heartbeat |

### Security keyword lists

| Constant | Values | Description |
|----------|--------|-------------|
| `HEALTHCARE_KEYWORDS` | `{'patient', 'medical', 'diagnosis', 'treatment', 'healthcare', 'clinical', 'hipaa', 'phi', 'medical record', 'prescription'}` | Keywords for healthcare pattern classification |
| `FINANCIAL_KEYWORDS` | `{'financial', 'payment', 'credit card', 'banking', 'transaction', 'pci dss', 'payment card'}` | Keywords for financial pattern classification |
| `PROPRIETARY_KEYWORDS` | `{'proprietary', 'confidential', 'internal', 'trade secret', 'company confidential', 'restricted'}` | Keywords for proprietary pattern classification |
| `SENSITIVE_PATTERN_TYPES` | `{'clinical_protocol', 'medical_guideline', 'patient_workflow', 'financial_procedure'}` | Sensitive pattern type identifiers |
| `INTERNAL_PATTERN_TYPES` | `{'architecture', 'business_logic', 'company_process'}` | Internal pattern type identifiers |
