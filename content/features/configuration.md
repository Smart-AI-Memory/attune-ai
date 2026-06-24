---
feature: configuration
summary: Layered configuration — the unified config tree, agent config, and the XML/empathy config layer
tags: [config, settings]
source_globs:
  - src/attune/config/**
nav:
  help: configuration
  mkdocs:
    how-to: how-to/configuration
    architecture: architecture/configuration
    reference: reference/configuration
---

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

## Quickstart

Load the unified config and validate it:

```python
from attune.config.loader import load_unified_config
from attune.config.validation import validate_config

cfg = load_unified_config()        # searches CONFIG_SEARCH_PATHS
errors = validate_config(cfg)
print(type(cfg).__name__, "with", len(errors), "validation error(s)")
print(cfg.routing.to_dict())
```

## Tasks

### Load and validate the unified config

**Goal:** get a typed `UnifiedConfig` and check it.

**Steps:**

```python
from attune.config.loader import load_unified_config
from attune.config.validation import validate_config

cfg = load_unified_config()
for err in validate_config(cfg):
    print(err)
```

**Verify:** `load_unified_config()` returns a `UnifiedConfig`;
`validate_config(cfg)` returns a `list[ValidationError]` (empty when the
config is valid).

### Read or write a nested value by key path

**Goal:** access a deeply nested field without walking sections.

**Steps:**

```python
from attune.config.loader import load_unified_config

cfg = load_unified_config()
keys = cfg.get_all_keys()          # every settable key path
value = cfg.get_value("routing.default_tier")
cfg.set_value("routing.default_tier", "capable")
```

**Verify:** `get_all_keys()` lists the key paths; `get_value` /
`set_value` read and write by dotted path.

### Override config from the environment

**Goal:** change a value without editing the file.

**Steps:** set an `ATTUNE_`-prefixed variable (the loader applies it
over the file value). `get_attune_env` also accepts the legacy
`EMPATHY_` prefix as a fallback.

```python
from attune.config.env_compat import get_attune_env

# reads ATTUNE_LOG_LEVEL, then EMPATHY_LOG_LEVEL, then the default
level = get_attune_env("LOG_LEVEL", default="INFO")
```

**Verify:** `get_attune_env(name, default)` returns the `ATTUNE_`-
prefixed value if set, else the `EMPATHY_`-prefixed value, else the
default.

### Load the legacy dataclass

**Goal:** interoperate with code that still uses `AttuneConfig`.

**Steps:**

```python
from attune.config import load_config

cfg = load_config()                # -> AttuneConfig (== EmpathyConfig)
```

**Verify:** `load_config(filepath=None, use_env=True)` returns an
`AttuneConfig`; it is the legacy dataclass, distinct from `UnifiedConfig`.

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

## Comparison

Four layers, distinct jobs:

| | Unified config | Agent config | XML/empathy config | Legacy dataclass |
|--|----------------|--------------|--------------------|------------------|
| Class | `UnifiedConfig` | `UnifiedAgentConfig` | `EmpathyXMLConfig` | `AttuneConfig` |
| Entry | `load_unified_config()` | construct / `for_book_production` | `get_config()` | `load_config()` |
| Scope | App-wide sections | LLM agent runtime | Empathy subsystem | Back-compat |
| Status | Modern (preferred) | Active | Active (subsystem) | Legacy |

`load_config()` and `load_unified_config()` return **different types**
(`AttuneConfig` vs `UnifiedConfig`) — they are not interchangeable.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `AttributeError` mixing the two configs | Treating a `UnifiedConfig` like an `AttuneConfig` (or vice versa) | They are different types — use one tree's API consistently | high |
| Env override ignored | Variable not `ATTUNE_`/`EMPATHY_`-prefixed, or set after load | Prefix correctly; reload after setting | medium |
| `validate_config` reports errors | A section value is out of range/invalid | Read each `ValidationError`; fix the named field | medium |
| `get_value`/`set_value` `KeyError` | Key path not in `get_all_keys()` | List `get_all_keys()` first | low |
| XML config changes not seen elsewhere | Replaced a local instance, not the global | Use `set_config()` to swap the global instance | medium |

### Risk areas

- **Two return types.** `load_config` → `AttuneConfig`;
  `load_unified_config` → `UnifiedConfig`. Don't cross their APIs.
- **Env precedence.** `ATTUNE_` wins over `EMPATHY_` wins over file.
- **Global XML config.** `get_config`/`set_config` operate on a shared
  instance; a local `EmpathyXMLConfig(...)` is not the global one.

### Diagnosis order

1. Which tree are you on? `type(cfg).__name__`.
2. For the unified tree, `validate_config(cfg)` then read each error.
3. For env issues, confirm the `ATTUNE_`/`EMPATHY_` prefix and load
   order.
4. For key-path issues, `cfg.get_all_keys()`.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** Author-curated seed
> questions, merged by the FAQ Generator with unmatched queries,
> telemetry, and issues. Not projected verbatim.

- **Q:** Which config should I use?
  **A:** The unified tree — `load_unified_config()` → `UnifiedConfig`
  with typed sections. `AttuneConfig`/`load_config()` is the legacy
  dataclass; `EmpathyXMLConfig` (`get_config()`) is the empathy
  subsystem's config.
- **Q:** Why are there `AttuneConfig` and `EmpathyConfig`?
  **A:** They are the **same class** — `EmpathyConfig` is an alias of
  `AttuneConfig` (the legacy dataclass).
- **Q:** How do environment overrides work?
  **A:** `ATTUNE_`-prefixed variables override file values; the legacy
  `EMPATHY_` prefix is honored as a fallback (`get_attune_env`).
- **Q:** Where does config load from?
  **A:** `CONFIG_SEARCH_PATHS` — `./attune.config.json`,
  `~/.attune/config.json`, `~/.config/attune/config.json`.

## Notes & tips

- **Prefer the unified tree for new code.** `UnifiedConfig` +
  `load_unified_config` + `validate_config` is the modern path.
- **`AttuneConfig` ≡ `EmpathyConfig`.** Same class, two names.
- **`load_config` and `load_unified_config` differ.** Different return
  types; pick one and stay consistent.
- **Use `set_config()` for the XML config.** It swaps the global
  instance other code reads.

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
