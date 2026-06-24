---
name: configuration
source: content/features/configuration.md
tags:
- config
- settings
type: reference
---

# Layered configuration — the unified config tree, agent config, and the XML/empathy config layer

## Reference

### `attune.config` (package top level)

| Symbol | Purpose |
|--------|---------|
| `load_config(filepath=None, use_env=True) -> AttuneConfig` | Load the legacy dataclass. |
| `AttuneConfig` / `EmpathyConfig` | The legacy config dataclass (same class). |
| `get_config() -> EmpathyXMLConfig` / `set_config(config)` | Read/replace the global XML/empathy config. |
| `EmpathyXMLConfig`, `XMLConfig`, `OptimizationConfig`, `AdaptiveConfig`, `I18nConfig`, `MetricsConfig` | XML/empathy config + sub-objects. |
| `UnifiedAgentConfig`, `BookProductionConfig` | Agent config. |
| `ModelTier`, `Provider`, `WorkflowMode` | Agent config enums. |
| `RedisConfig` | Redis section. |

### `attune.config.loader`

| Symbol | Purpose |
|--------|---------|
| `load_unified_config(path=None) -> UnifiedConfig` | Load the unified tree. |
| `save_unified_config(...)` | Persist a `UnifiedConfig`. |
| `ConfigLoader` | Loader class (`load`, `save`, `get_config`, `apply_env_overrides`, `discover_config_path`). |
| `CONFIG_SEARCH_PATHS` | The ordered search paths. |

### `attune.config.unified` / `.sections` / `.validation` / `.env_compat`

| Symbol | Purpose |
|--------|---------|
| `UnifiedConfig` | Modern config; sections + `get_value`/`set_value`/`get_all_keys`. |
| `AnalysisConfig`, `AuthConfig`, `EnvironmentConfig`, `PersistenceConfig`, `RoutingConfig`, `TelemetryConfig`, `WorkflowConfig` | The seven sections. |
| `validate_config(config) -> list[ValidationError]`, `ValidationError`, `ConfigValidator` | Validation. |
| `get_attune_env(name, default=None)`, `iter_attune_env_prefix(prefix, suffix="")` | `ATTUNE_`/`EMPATHY_` env access. |
