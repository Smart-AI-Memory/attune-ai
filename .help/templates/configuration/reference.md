---
feature: configuration
depth: reference
generated_at: 2026-06-03T02:40:23.636631+00:00
source_hash: c8fb692ea17a00968fafe6e570ae09d569d1880728837d9636497e05d1a9d9ed
status: generated
---

# Configuration reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `ModelTier` | Model tier for cost optimization. | `src/attune/config/agent_config.py` |
| `Provider` | LLM provider options. | `src/attune/config/agent_config.py` |
| `WorkflowMode` | Workflow execution modes. | `src/attune/config/agent_config.py` |
| `AgentOperationError` | Error during agent operation with context. | `src/attune/config/agent_config.py` |
| `UnifiedAgentConfig` | Unified configuration model for all agents. | `src/attune/config/agent_config.py` |
| `MemDocsConfig` | Configuration for MemDocs pattern storage integration. | `src/attune/config/agent_config.py` |
| `RedisConfig` | Configuration for Redis state management. | `src/attune/config/agent_config.py` |
| `BookProductionConfig` | Unified configuration for book production agents. | `src/attune/config/agent_config.py` |
| `WorkflowConfig` | Configuration for agent workflows. | `src/attune/config/agent_config.py` |
| `ConfigLoader` | Load, save, and manage Attune AI configuration. | `src/attune/config/loader.py` |
| `AnalysisConfig` | Code analysis and scanning configuration. | `src/attune/config/sections/analysis.py` |
| `AuthConfig` | Authentication and API key configuration. | `src/attune/config/sections/auth.py` |
| `EnvironmentConfig` | Environment and display configuration. | `src/attune/config/sections/environment.py` |
| `PersistenceConfig` | Data persistence and memory configuration. | `src/attune/config/sections/persistence.py` |
| `RoutingConfig` | Model routing and tier selection configuration. | `src/attune/config/sections/routing.py` |
| `TelemetryConfig` | Telemetry and usage tracking configuration. | `src/attune/config/sections/telemetry.py` |
| `WorkflowConfig` | Workflow execution configuration. | `src/attune/config/sections/workflows.py` |
| `UnifiedConfig` | Unified configuration for Attune AI. | `src/attune/config/unified.py` |
| `ValidationError` | Represents a configuration validation error. | `src/attune/config/validation.py` |
| `ConfigValidator` | Validate Attune AI configuration. | `src/attune/config/validation.py` |
| `XMLConfig` | XML prompting configuration. | `src/attune/config/xml_config.py` |
| `OptimizationConfig` | Context window optimization configuration. | `src/attune/config/xml_config.py` |
| `AdaptiveConfig` | Adaptive prompting configuration. | `src/attune/config/xml_config.py` |
| `I18nConfig` | Internationalization configuration. | `src/attune/config/xml_config.py` |
| `MetricsConfig` | Metrics tracking configuration. | `src/attune/config/xml_config.py` |
| `EmpathyXMLConfig` | Main Empathy XML enhancement configuration. | `src/attune/config/xml_config.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `get_attune_env()` | Get an environment variable, checking ATTUNE_ first then EMPATHY_ fallback. | `src/attune/config/env_compat.py` |
| `iter_attune_env_prefix()` | Yield (middle_part, value) for env vars matching ATTUNE_{prefix}*{suffix}. | `src/attune/config/env_compat.py` |
| `get_loader()` | Get the global ConfigLoader instance. | `src/attune/config/loader.py` |
| `load_unified_config()` | Convenience function to load unified configuration. | `src/attune/config/loader.py` |
| `save_unified_config()` | Convenience function to save unified configuration. | `src/attune/config/loader.py` |
| `validate_config()` | Convenience function to validate configuration. | `src/attune/config/validation.py` |
| `get_config()` | Get global configuration instance. | `src/attune/config/xml_config.py` |
| `set_config()` | Set global configuration instance. | `src/attune/config/xml_config.py` |


## Source files

- `src/attune/config/**`

## Tags

`config`, `settings`
