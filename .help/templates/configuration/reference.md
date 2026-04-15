---
type: reference
feature: configuration
depth: reference
generated_at: 2026-04-14T15:29:59.668081+00:00
source_hash: 4aba109a0dfc8d51fc39c5be662b4c0ce340e3fe680c780d425e04060f8e199d
status: generated
---

# Configuration reference

## Classes

### Configuration Data Models

| Class | Description |
|-------|-------------|
| `UnifiedAgentConfig` | Unified configuration model for all agents |
| `BookProductionConfig` | Unified configuration for book production agents |
| `MemDocsConfig` | Configuration for MemDocs pattern storage integration |
| `RedisConfig` | Configuration for Redis state management |
| `WorkflowConfig` | Configuration for agent workflows |
| `AnalysisConfig` | Code analysis and scanning configuration |
| `AuthConfig` | Authentication and API key configuration |
| `EnvironmentConfig` | Environment and display configuration |
| `PersistenceConfig` | Data persistence and memory configuration |
| `RoutingConfig` | Model routing and tier selection configuration |
| `TelemetryConfig` | Telemetry and usage tracking configuration |
| `UnifiedConfig` | Unified configuration for Attune AI |
| `XMLConfig` | XML prompting configuration |
| `OptimizationConfig` | Context window optimization configuration |
| `AdaptiveConfig` | Adaptive prompting configuration |
| `I18nConfig` | Internationalization configuration |
| `MetricsConfig` | Metrics tracking configuration |
| `EmpathyXMLConfig` | Main Empathy XML enhancement configuration |

### Enumerations

| Enum | Description |
|------|-------------|
| `ModelTier` | Model tier for cost optimization |
| `Provider` | LLM provider options |
| `WorkflowMode` | Workflow execution modes |

### Management Classes

| Class | Description |
|-------|-------------|
| `ConfigLoader` | Load, save, and manage Attune AI configuration |
| `ConfigValidator` | Validate Attune AI configuration |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `AgentOperationError` | Error during agent operation with context |
| `ValidationError` | Represents a configuration validation error |

## Key Class Details

### ConfigLoader Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `config_path: str \| Path \| None = None` | `None` | Initialize configuration loader |
| `discover_config_path` | | `Path \| None` | Discover configuration file path |
| `get_default_config_path` | | `Path` | Get default configuration file path |
| `get_config_path` | | `Path \| None` | Get current configuration file path |
| `load` | | `UnifiedConfig` | Load configuration from file |
| `save` | `config: UnifiedConfig, path: Path \| None = None` | `Path` | Save configuration to file |
| `apply_env_overrides` | `config: UnifiedConfig` | `UnifiedConfig` | Apply environment variable overrides |
| `get_config` | | `UnifiedConfig` | Get current configuration |

### UnifiedAgentConfig Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `normalize_role` | `cls, v: str` | `str` | Normalize role string |
| `get_model_id` | | `str` | Get model identifier |
| `for_book_production` | | `BookProductionConfig` | Create book production configuration |

### BookProductionConfig Properties

| Property | Type | Description |
|----------|------|-------------|
| `model` | `str` | Get model ID for backward compatibility |
| `max_tokens` | `int` | Get max tokens for backward compatibility |
| `temperature` | `float` | Get temperature for backward compatibility |
| `timeout` | `int` | Get timeout for backward compatibility |
| `retry_attempts` | `int` | Get retry attempts for backward compatibility |
| `retry_delay` | `float` | Get retry delay for backward compatibility |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_attune_env` | `name: str, default: str \| None = None` | `str \| None` | Get environment variable, checking ATTUNE_ first then EMPATHY_ fallback |
| `iter_attune_env_prefix` | `prefix: str, suffix: str = ''` | `Iterator[tuple[str, str]]` | Yield (middle_part, value) for env vars matching ATTUNE_{prefix}*{suffix} |
| `get_loader` | | `ConfigLoader` | Get the global ConfigLoader instance |
| `load_unified_config` | `path: str \| Path \| None = None` | `UnifiedConfig` | Load unified configuration |
| `save_unified_config` | `config: UnifiedConfig, path: str \| Path \| None = None` | `Path` | Save unified configuration |
| `validate_config` | `config: UnifiedConfig` | `list[ValidationError]` | Validate configuration |
| `get_config` | | `EmpathyXMLConfig` | Get global configuration instance |
| `set_config` | `config: EmpathyXMLConfig` | `None` | Set global configuration instance |

## Constants

| Constant | Value | Description |
|----------|--------|-------------|
| `ENV_PREFIX` | `'ATTUNE_'` | Environment variable prefix |
| `CONFIG_SEARCH_PATHS` | `['./attune.config.json', '~/.attune/config.json', '~/.config/attune/config.json']` | Default configuration file search paths |
