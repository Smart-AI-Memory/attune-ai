---
type: concept
name: configuration-concept
feature: configuration
depth: concept
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 5e48805be1a999be45deb9a9c24e4965ca3ad0e741320a5c68a4675f40612ac8
status: generated
---

# Configuration

Attune's configuration system is a layered set of typed dataclasses, a file loader, and an environment-variable compatibility layer that together resolve a single `UnifiedConfig` object at runtime.

## The two config trees

The system has two distinct trees that serve different purposes:

**Agent configuration** (`config.agent_config`) models the runtime behavior of LLM-backed agents. `UnifiedAgentConfig` is the central class: it normalizes agent roles via `normalize_role`, resolves a model identifier via `get_model_id`, and produces a `BookProductionConfig` view via `for_book_production`. `BookProductionConfig` exposes backward-compatible properties — `model`, `max_tokens`, `temperature`, `timeout`, `retry_attempts`, and `retry_delay` — so older call sites continue to work while the underlying config evolves. Supporting enumerations `ModelTier`, `Provider`, and `WorkflowMode` constrain the values callers can supply, catching bad input before it reaches an API call.

**Unified application configuration** (`config.unified`, `config.sections`) organizes everything else into named sections: `AnalysisConfig`, `AuthConfig`, `EnvironmentConfig`, `PersistenceConfig`, `RoutingConfig`, `TelemetryConfig`, and `WorkflowConfig`. Each section implements `to_dict` and `from_dict`, so it can round-trip through YAML or JSON without losing type information. `UnifiedConfig` wraps all sections and adds `get_value`, `set_value`, and `get_all_keys` for key-path access when you need to read or write a deeply nested field by name.

## How values are resolved

`ConfigLoader` orchestrates loading and saving. When you call `load_unified_config()`, the loader:

1. Searches `CONFIG_SEARCH_PATHS` (`./attune.config.json`, `~/.attune/config.json`, `~/.config/attune/config.json`) via `discover_config_path`.
2. Deserializes the file into a `UnifiedConfig` using each section's `from_dict`.
3. Applies environment-variable overrides through `apply_env_overrides`.

Environment variables take precedence over file values. `get_attune_env` checks `ATTUNE_`-prefixed variables first, then falls back to the legacy `EMPATHY_` prefix, so projects migrating from an older prefix do not need to update their environment immediately. `iter_attune_env_prefix` lets you scan all variables that match a given `ATTUNE_{prefix}*{suffix}` pattern, which is how bulk overrides (for example, overriding every routing key at once) are applied.

After loading, pass the result to `validate_config` to get a list of `ValidationError` objects before any agent work begins. `ConfigValidator.validate_section` lets you target a single section if you only need to check part of the config.

## The XML/empathy config layer

`EmpathyXMLConfig` is a separate global config object used by the empathy subsystem. You load it with `EmpathyXMLConfig.load_from_file` (defaulting to `.attune/config.json`) or build it from the environment with `EmpathyXMLConfig.from_env`. The module-level `get_config` and `set_config` functions let any part of the codebase read or replace the active instance without holding a direct reference to it. Its sub-objects — `XMLConfig`, `OptimizationConfig`, `AdaptiveConfig`, `I18nConfig`, and `MetricsConfig` — cover rendering, optimization hints, internationalization, and metrics collection respectively.

## When each part matters

| Situation | What to reach for |
|---|---|
| Configuring an agent's model, tokens, or retry behavior | `UnifiedAgentConfig` → `BookProductionConfig` |
| Reading or writing a named config value at runtime | `UnifiedConfig.get_value` / `set_value` |
| Loading config from disk in one call | `load_unified_config()` |
| Persisting changes back to disk | `save_unified_config()` |
| Checking config before starting a workflow | `validate_config()` |
| Reading an env var with legacy-prefix fallback | `get_attune_env()` |
| Accessing the empathy subsystem's global config | `get_config()` / `set_config()` |
