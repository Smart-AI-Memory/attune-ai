---
type: reference
name: configuration-reference
feature: configuration
depth: reference
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 5e48805be1a999be45deb9a9c24e4965ca3ad0e741320a5c68a4675f40612ac8
status: generated
---

# Configuration reference

Load, validate, and manage Attune AI configuration across agents, workflows, and environments.

## Classes

| Class | Description |
|-------|-------------|
| `ModelTier` | Model tier for cost optimization. |
| `Provider` | LLM provider options. |
| `WorkflowMode` | Workflow execution modes. |
| `AgentOperationError` | Error during agent operation with context. |
| `UnifiedAgentConfig` | Unified configuration model for all agents. |
| `MemDocsConfig` | Configuration for MemDocs pattern storage integration. |
| `RedisConfig` | Configuration for Redis state management. |
| `BookProductionConfig` | Unified configuration for book production agents. |
| `WorkflowConfig` | Configuration for agent workflows. |
| `ConfigLoader` | Load, save, and manage Attune AI configuration. |
| `AnalysisConfig` | Code analysis and scanning configuration. |
| `AuthConfig` | Authentication and API key configuration. |
| `EnvironmentConfig` | Environment and display configuration. |
| `PersistenceConfig` | Data persistence and memory configuration. |
| `RoutingConfig` | Model routing and tier selection configuration. |
| `TelemetryConfig` | Telemetry and usage tracking configuration. |
| `WorkflowConfig` | Workflow execution configuration. |
| `UnifiedConfig` | Unified configuration for Attune AI. |
| `ValidationError` | Represents a configuration validation error. |
| `ConfigValidator` | Validate Attune AI configuration. |
| `XMLConfig` | XML prompting configuration. |
| `OptimizationConfig` | Context window optimization configuration. |
| `AdaptiveConfig` | Adaptive prompting configuration. |
| `I18nConfig` | Internationalization configuration. |
| `MetricsConfig` | Metrics tracking configuration. |
| `EmpathyXMLConfig` | Main Empathy XML enhancement configuration. |

### `BookProductionConfig` properties

| Property | Type | Description |
|----------|------|-------------|
| `model` | `str` | Get model ID for backward compatibility. |
| `max_tokens` | `int` | Get max tokens for backward compatibility. |
| `temperature` | `float` | Get temperature for backward compatibility. |
| `timeout` | `int` | Get timeout for backward compatibility. |
| `retry_attempts` | `int` | Get retry attempts for backward compatibility. |
| `retry_delay` | `float` | Get retry delay for backward compatibility. |

### `ConfigLoader` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `config_path: str | Path | None = None` | `None` | Initialize the loader with an optional config path. |
| `discover_config_path` | — | `Path | None` | Discover a config file from the standard search paths. |
| `get_default_config_path` | — | `Path` | Return the default config file path. |
| `get_config_path` | — | `Path | None` | Return the config path this loader was initialized with. |
| `load` | — | `UnifiedConfig` | Load configuration from disk. |
| `save` | `config: UnifiedConfig, path: Path | None = None` | `Path` | Save configuration to disk and return the written path. |
| `apply_env_overrides` | `config: UnifiedConfig` | `UnifiedConfig` | Apply environment variable overrides to a config object. |
| `get_config` | — | `UnifiedConfig` | Return the loaded configuration, loading it if necessary. |

### `UnifiedAgentConfig` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `normalize_role` | `v: str` | `str` | Normalize a role string value. |
| `get_model_id` | — | `str` | Return the model ID for this agent configuration. |
| `for_book_production` | — | `BookProductionConfig` | Return a `BookProductionConfig` derived from this config. |

### `UnifiedConfig` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `touch` | — | `None` | Mark the config as modified. |
| `to_dict` | — | `dict` | Serialize the config to a dictionary. |
| `from_dict` | `data: dict` | `UnifiedConfig` | Deserialize a config from a dictionary. |
| `get_value` | `key: str` | `object` | Return the value for the given key. |
| `set_value` | `key: str, value: object` | `None` | Set the value for the given key. |
| `get_all_keys` | — | `list[str]` | Return all keys present in the config. |

### `EmpathyXMLConfig` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `load_from_file` | `config_file: str = '.attune/config.json'` | `EmpathyXMLConfig` | Load configuration from a JSON file. |
| `save_to_file` | `config_file: str = '.attune/config.json'` | `None` | Save configuration to a JSON file. |
| `from_env` | — | `EmpathyXMLConfig` | Build configuration from environment variables. |

### `ConfigValidator` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `validate` | `config: UnifiedConfig` | `list[ValidationError]` | Validate a `UnifiedConfig` and return any errors found. |
| `validate_section` | `section: Any, section_name: str` | `list[ValidationError]` | Validate a single config section and return any errors found. |

### Section config methods

Each of `AnalysisConfig`, `AuthConfig`, `EnvironmentConfig`, `PersistenceConfig`, `RoutingConfig`, `TelemetryConfig`, and `WorkflowConfig` exposes the following methods:

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | — | `dict` | Serialize the section to a dictionary. |
| `from_dict` | `data: dict` | *(section class)* | Deserialize the section from a dictionary. |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_attune_env` | `name: str, default: str \| None = None` | `str \| None` | Get an environment variable, checking `ATTUNE_` first then `EMPATHY_` fallback. |
| `iter_attune_env_prefix` | `prefix: str, suffix: str = ''` | `Iterator[tuple[str, str]]` | Yield `(middle_part, value)` for env vars matching `ATTUNE_{prefix}*{suffix}`. |
| `get_loader` | — | `ConfigLoader` | Return the global `ConfigLoader` instance. |
| `load_unified_config` | `path: str \| Path \| None = None` | `UnifiedConfig` | Load unified configuration from the given path, or discover it automatically. |
| `save_unified_config` | `config: UnifiedConfig, path: str \| Path \| None = None` | `Path` | Save unified configuration to the given path and return the written path. |
| `validate_config` | `config: UnifiedConfig` | `list[ValidationError]` | Validate a `UnifiedConfig` and return all validation errors. |
| `get_config` | — | `EmpathyXMLConfig` | Return the global `EmpathyXMLConfig` instance. |
| `set_config` | `config: EmpathyXMLConfig` | `None` | Replace the global `EmpathyXMLConfig` instance. |

## Constants

| Constant | Type | Values |
|----------|------|--------|
| `ENV_PREFIX` | `str` | `'ATTUNE_'` |
| `CONFIG_SEARCH_PATHS` | `list` | `'./attune.config.json'`, `'~/.attune/config.json'`, `'~/.config/attune/config.json'` |

## Source files

- `src/attune/config/**`

## Tags

`config`, `settings`
