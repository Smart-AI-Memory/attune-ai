---
type: note
name: configuration-note
feature: configuration
depth: note
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 5e48805be1a999be45deb9a9c24e4965ca3ad0e741320a5c68a4675f40612ac8
status: generated
---

# Note: Configuration

## How the configuration surface is organized

The `config` package exposes two kinds of public symbols: **section dataclasses** that hold typed values, and **top-level functions** that load, save, and validate those values.

The section dataclasses cover distinct concerns:

| Class | Purpose |
|---|---|
| `UnifiedAgentConfig` | Unified configuration model for all agents |
| `BookProductionConfig` | Runtime parameters for book production agents (model, token limits, timeouts, retry behavior) |
| `MemDocsConfig` | MemDocs pattern storage integration settings |
| `RedisConfig` | Redis state management settings |
| `ModelTier` | Model tier selection for cost optimization |
| `Provider` | LLM provider options |
| `WorkflowMode` | Workflow execution modes |

Section dataclasses in `config.sections` (`AnalysisConfig`, `AuthConfig`, `EnvironmentConfig`, `PersistenceConfig`, `RoutingConfig`, `TelemetryConfig`, `WorkflowConfig`) each expose `to_dict()` and `from_dict()` for serialization. `UnifiedConfig` composes these sections and adds `get_value()`, `set_value()`, and `get_all_keys()` for key-based access.

The top-level functions wrap `ConfigLoader` for convenience:

| Function | What it does |
|---|---|
| `load_unified_config()` | Loads a `UnifiedConfig` from a path or from a discovered location |
| `save_unified_config()` | Saves a `UnifiedConfig` and returns the path written |
| `get_loader()` | Returns the global `ConfigLoader` instance |
| `validate_config()` | Returns a list of `ValidationError` objects for a given `UnifiedConfig` |
| `get_config()` / `set_config()` | Get or replace the global `EmpathyXMLConfig` instance |

## Environment variable behavior

`get_attune_env(name)` checks the `ATTUNE_` prefix first, then falls back to the legacy `EMPATHY_` prefix. This means existing `EMPATHY_*` variables continue to work without changes.

`iter_attune_env_prefix(prefix, suffix)` yields `(middle_part, value)` tuples for all variables matching `ATTUNE_{prefix}*{suffix}`, which lets the loader enumerate families of related variables (for example, all provider API keys) without hardcoding each name.

`ConfigLoader.apply_env_overrides()` applies these environment values on top of whatever was read from disk, so environment variables always win over file-based settings.

## Config file discovery

`ConfigLoader` searches for a configuration file in the following locations, in order:

- `./attune.config.json`
- `~/.attune/config.json`
- `~/.config/attune/config.json`

`ConfigLoader.discover_config_path()` returns the first path that exists, or `None` if none do. `ConfigLoader.get_default_config_path()` returns the default write location regardless of whether the file exists. `EmpathyXMLConfig.load_from_file()` and `save_to_file()` use `.attune/config.json` by default.

## Two config subsystems

The package contains two distinct configuration subsystems that coexist:

- **`UnifiedConfig` + `ConfigLoader`** — the primary system for agent and workflow configuration, loaded via `load_unified_config()`.
- **`EmpathyXMLConfig`** — an older global-singleton system accessed via `get_config()` and `set_config()`, with XML-oriented sub-configs (`XMLConfig`, `OptimizationConfig`, `AdaptiveConfig`, `I18nConfig`, `MetricsConfig`). It can also be populated from environment variables via `EmpathyXMLConfig.from_env()`.

Code that reads agent settings should use `UnifiedAgentConfig` and `load_unified_config()`. The `EmpathyXMLConfig` path exists for compatibility with earlier tooling.
