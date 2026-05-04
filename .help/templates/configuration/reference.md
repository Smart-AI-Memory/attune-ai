---
type: reference
feature: configuration
depth: reference
generated_at: 2026-05-04T02:41:08.507521+00:00
source_hash: b67c4428689dde6c18aca17808e3037eded03448162cc3406741340bbe33b804
status: generated
---

# Configuration reference

Comprehensive configuration system for Attune AI agents, workflows, and application settings. Includes type-safe config classes, environment variable compatibility, and unified configuration management.

## Classes

| Class | Description |
|-------|-------------|
| `ModelTier` | Model tier for cost optimization |
| `Provider` | LLM provider options |
| `WorkflowMode` | Workflow execution modes |
| `AgentOperationError` | Error during agent operation with context |
| `UnifiedAgentConfig` | Unified configuration model for all agents |
| `MemDocsConfig` | Configuration for MemDocs pattern storage integration |
| `RedisConfig` | Configuration for Redis state management |
| `BookProductionConfig` | Unified configuration for book production agents |
| `WorkflowConfig` | Configuration for agent workflows |
| `ConfigLoader` | Load, save, and manage Attune AI configuration |
| `AnalysisConfig` | Code analysis and scanning configuration |
| `AuthConfig` | Authentication and API key configuration |
| `EnvironmentConfig` | Environment and display configuration |
| `PersistenceConfig` | Data persistence and memory configuration |
| `RoutingConfig` | Model routing and tier selection configuration |
| `TelemetryConfig` | Telemetry and usage tracking configuration |
| `UnifiedConfig` | Unified configuration for Attune AI |
| `ValidationError` | Represents a configuration validation error |
| `ConfigValidator` | Validate Attune AI configuration |
| `XMLConfig` | XML prompting configuration |
| `OptimizationConfig` | Context window optimization configuration |
| `AdaptiveConfig` | Adaptive prompting configuration |
| `I18nConfig` | Internationalization configuration |
| `MetricsConfig` | Metrics tracking configuration |
| `EmpathyXMLConfig` | Main Empathy XML enhancement configuration |

### AgentOperationError

Exception class for agent operation failures.

| Method | Parameters | Description |
|--------|------------|-------------|
| `__init__` | `operation: str, cause: Exception` | Initialize with operation name and underlying cause |

### UnifiedAgentConfig

Core configuration model for Attune AI agents.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `normalize_role` | `v: str` | `str` | Normalize role string for consistency |
| `get_model_id` | | `str` | Get the model identifier |
| `for_book_production` | | `BookProductionConfig` | Convert to book production configuration |

### BookProductionConfig

Configuration for book production workflows with backward compatibility properties.

| Property | Type | Description |
|----------|------|-------------|
| `model` | `str` | Get model ID for backward compatibility |
| `max_tokens` | `int` | Get max tokens for backward compatibility |
| `temperature` | `float` | Get temperature for backward compatibility |
| `timeout` | `int` | Get timeout for backward compatibility |
| `retry_attempts` | `int` | Get retry attempts for backward compatibility |
| `retry_delay` | `float` | Get retry delay for backward compatibility |

### ConfigLoader

Primary interface for loading and saving Attune AI configuration.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `config_path: str \| Path \| None = None` | `None` | Initialize with optional config path |
| `discover_config_path` | | `Path \| None` | Find configuration file in standard locations |
| `get_default_config_path` | | `Path` | Get the default configuration file path |
| `get_config_path` | | `Path \| None` | Get the current configuration file path |
| `load` | | `UnifiedConfig` | Load configuration from file |
| `save` | `config: UnifiedConfig, path: Path \| None = None` | `Path` | Save configuration to file |
| `apply_env_overrides` | `config: UnifiedConfig` | `UnifiedConfig` | Apply environment variable overrides |
| `get_config` | | `UnifiedConfig` | Get current configuration |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_attune_env` | `name: str, default: str \| None = None` | `str \| None` | Get an environment variable, checking ATTUNE_ first then EMPATHY_ fallback |
| `iter_attune_env_prefix` | `prefix: str, suffix: str = ''` | `Iterator[tuple[str, str]]` | Yield (middle_part, value) for env vars matching ATTUNE_{prefix}*{suffix} |
| `get_loader` | | `ConfigLoader` | Get the global ConfigLoader instance |
| `load_unified_config` | `path: str \| Path \| None = None` | `UnifiedConfig` | Convenience function to load unified configuration |
| `save_unified_config` | `config: UnifiedConfig, path: str \| Path \| None = None` | `Path` | Convenience function to save unified configuration |
| `validate_config` | `config: UnifiedConfig` | `list[ValidationError]` | Convenience function to validate configuration |
| `get_config` | | `EmpathyXMLConfig` | Get global configuration instance |
| `set_config` | `config: EmpathyXMLConfig` | `None` | Set global configuration instance |

## Constants

| Constant | Values | Description |
|----------|--------|-------------|
| `CONFIG_SEARCH_PATHS` | `['./attune.config.json', '~/.attune/config.json', '~/.config/attune/config.json']` | Standard configuration file locations |
| `ENV_PREFIX` | `'ATTUNE_'` | Environment variable prefix |
