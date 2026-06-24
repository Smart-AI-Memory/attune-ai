# Configuration

## Overview

Attune's configuration lives under `attune.config` and is **layered** —
several typed systems that serve different parts of the framework. The
one most code reaches for is the **unified config tree**; alongside it
are an **agent config** layer, an **XML/empathy config** layer, and a
**legacy dataclass** kept for backward compatibility.

The four layers, and when each matters:

- **Unified application config** — `UnifiedConfig` (`config.unified`)
  organized into named sections (`config.sections`), loaded and saved by
  `ConfigLoader` / `load_unified_config` (`config.loader`) and checked by
  `validate_config` (`config.validation`). This is the modern structured
  config.
- **Agent config** — `UnifiedAgentConfig` and `BookProductionConfig`
  (`config.agent_config`), constrained by the `ModelTier`, `Provider`,
  and `WorkflowMode` enums — the runtime behavior of LLM-backed agents.
- **XML/empathy config** — `EmpathyXMLConfig`, the global instance read
  and replaced via `get_config()` / `set_config()`, with sub-objects
  `XMLConfig`, `OptimizationConfig`, `AdaptiveConfig`, `I18nConfig`,
  `MetricsConfig`.
- **Legacy dataclass** — `AttuneConfig` (aliased as `EmpathyConfig`),
  loaded by `load_config()`. Kept for backward compatibility; new code
  should prefer the unified tree.

## Concepts

### The unified config tree

`UnifiedConfig` is the modern config object. It holds seven typed
sections — `analysis`, `auth`, `environment`, `persistence`, `routing`,
`telemetry`, `workflows` (the classes in `config.sections`:
`AnalysisConfig`, `AuthConfig`, `EnvironmentConfig`, `PersistenceConfig`,
`RoutingConfig`, `TelemetryConfig`, `WorkflowConfig`). Each section
round-trips through `to_dict` / `from_dict`. `UnifiedConfig` adds
key-path access — `get_value`, `set_value`, `get_all_keys` — for reading
or writing a nested field by name.

`ConfigLoader` (`config.loader`) orchestrates loading and saving;
`load_unified_config(path=None)` is the convenience entry. The loader
searches `CONFIG_SEARCH_PATHS` (`./attune.config.json`,
`~/.attune/config.json`, `~/.config/attune/config.json`), deserializes
into a `UnifiedConfig`, and applies environment overrides. Env variables
take precedence: `get_attune_env` (`config.env_compat`) reads
`ATTUNE_`-prefixed variables first and falls back to the legacy
`EMPATHY_` prefix, so a project migrating prefixes need not update its
environment immediately.

`validate_config(config)` (`config.validation`) returns a list of
`ValidationError` for a `UnifiedConfig`; `ConfigValidator` lets you
validate a single section.

### Agent config

`UnifiedAgentConfig` (`config.agent_config`) models how LLM-backed
agents run. `BookProductionConfig` is a backward-compatible view exposing
properties like `model`, `max_tokens`, `temperature`, `timeout`. The
enums `ModelTier`, `Provider`, and `WorkflowMode` constrain the values
callers may supply, catching bad input before it reaches an API call.

### The XML/empathy config layer

`EmpathyXMLConfig` is a separate global config used by the empathy
subsystem. Load it with `EmpathyXMLConfig.load_from_file(config_file=
".attune/config.json")` or `EmpathyXMLConfig.from_env()`; the
module-level `get_config()` / `set_config()` read or replace the active
instance without holding a direct reference. Its sub-objects —
`XMLConfig`, `OptimizationConfig`, `AdaptiveConfig`, `I18nConfig`,
`MetricsConfig` — cover rendering, optimization hints, i18n, and metrics.

### The legacy dataclass

`AttuneConfig` (exported also as `EmpathyConfig` — the same class) is the
older empathy-era dataclass. `load_config(filepath=None, use_env=True)`
returns one. It carries `from_yaml` / `to_yaml` / `from_env` /
`validate`. New code should prefer the unified tree; this remains for
back-compat.

## Design & extension

### Design decisions

- **Sectioned unified config.** Splitting `UnifiedConfig` into typed
  sections keeps each concern cohesive and round-trippable via
  `to_dict`/`from_dict`.
- **Env compatibility shim.** `get_attune_env` honors both `ATTUNE_`
  and legacy `EMPATHY_` prefixes so prefix migration is non-breaking.
- **Layers, not one config.** Agent config, the XML/empathy config, and
  the legacy dataclass coexist deliberately — each serves a subsystem;
  the unified tree is the modern front door.

### Extension points

- **Add a setting:** extend the relevant `config.sections` dataclass
  (it gets `to_dict`/`from_dict` round-tripping and key-path access).
- **Custom validation:** add to `config.validation` /
  `ConfigValidator`.
- **New env override:** read it via `get_attune_env` /
  `iter_attune_env_prefix`.

<!-- attune-generated: source_hash=7359a1b70578c0d83b0fc6af405ebd38e3949c66a7f64b303c05e961504871c1 feature=configuration kind=architecture generated_at=2026-06-24 -->
