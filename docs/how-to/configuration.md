# Configuration

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

<!-- attune-generated: source_hash=7359a1b70578c0d83b0fc6af405ebd38e3949c66a7f64b303c05e961504871c1 feature=configuration kind=how-to generated_at=2026-06-24 -->
