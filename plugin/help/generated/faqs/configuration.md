---
name: configuration
source: content/features/configuration.md
tags:
- config
- settings
type: faq
---

# Configuration FAQ

## What does the configuration module do?

It loads, validates, and manages all Attune AI settings — agent behavior, workflows, persistence, routing, telemetry, auth, and more — from config files, environment variables, or both.

## How do I load configuration?

Call `load_unified_config()` for a one-liner, or instantiate `ConfigLoader` directly if you need more control (for example, to pass a specific path or call `apply_env_overrides()` separately).

```python
from attune.config.loader import load_unified_config

config = load_unified_config()          # auto-discovers config file
config = load_unified_config("my/path/attune.config.json")  # explicit path
```

## Where does the loader look for config files?

`ConfigLoader.discover_config_path()` searches these paths in order:

- `./attune.config.json`
- `~/.attune/config.json`
- `~/.config/attune/config.json`

The first file found wins. If none exist, `get_default_config_path()` returns the default location to write a new one.

## How do environment variables override config file values?

Call `ConfigLoader.apply_env_overrides(config)` after loading. Environment variables use the prefix `ATTUNE_`. If an `ATTUNE_`-prefixed variable is not set, the module falls back to the equivalent `EMPATHY_`-prefixed variable via `get_attune_env()`.

## How do I read a single environment variable?

Use `get_attune_env(name, default)`. It checks `ATTUNE_{name}` first, then `EMPATHY_{name}`, and returns `default` if neither is set.

```python
from attune.config.env_compat import get_attune_env

api_key = get_attune_env("API_KEY", default=None)
```

## How do I iterate over a group of related environment variables?

Use `iter_attune_env_prefix(prefix, suffix)`. It yields `(middle_part, value)` for every env var matching `ATTUNE_{prefix}*{suffix}`.

```python
from attune.config.env_compat import iter_attune_env_prefix

for name, value in iter_attune_env_prefix("MODEL_"):
    print(name, value)
```

## How do I save configuration back to disk?

Use `save_unified_config(config, path)` or `ConfigLoader.save(config, path)`. Both return the `Path` where the file was written.

## How do I validate a config object?

Pass a `UnifiedConfig` instance to `validate_config()`. It returns a list of `ValidationError` objects — an empty list means the config is valid.

```python
from attune.config.validation import validate_config

errors = validate_config(config)
if errors:
    for e in errors:
        print(e)
```

## What sections does `UnifiedConfig` contain?

`UnifiedConfig` composes these section classes, all importable from `attune.config.sections`:

| Section | Class |
|---|---|
| Analysis | `AnalysisConfig` |
| Auth | `AuthConfig` |
| Environment | `EnvironmentConfig` |
| Persistence | `PersistenceConfig` |
| Routing | `RoutingConfig` |
| Telemetry | `TelemetryConfig` |
| Workflows | `WorkflowConfig` |

Each section has `to_dict()` and `from_dict()` methods for serialization.

## How do I read or write individual values on a `UnifiedConfig`?

Use `get_value(key)`, `set_value(key, value)`, and `get_all_keys()` to work with config values without accessing section attributes directly.

## What is `EmpathyXMLConfig` and when do I use it?

`EmpathyXMLConfig` is a separate config object for the Empathy subsystem. Load it with `EmpathyXMLConfig.load_from_file()` or build it from environment variables with `EmpathyXMLConfig.from_env()`. Use `get_config()` and `set_config()` to access or replace the global instance.

## How do I configure agent behavior?

Use `UnifiedAgentConfig`. Call `get_model_id()` to resolve the active model, and `for_book_production()` to get a `BookProductionConfig` scoped to book-production agents. `BookProductionConfig` exposes `model`, `max_tokens`, `temperature`, `timeout`, `retry_attempts`, and `retry_delay` as properties.

## How do I debug a configuration problem?

1. Run `pytest -k "configuration" -v` to check whether the issue is in your code or the library.
2. Call `validate_config(config)` and inspect any returned `ValidationError` objects.
3. Print `config.get_all_keys()` to confirm which keys are present.
4. Check that your environment variables carry the `ATTUNE_` prefix and use `get_attune_env()` to verify they resolve correctly.

## Where is the source code?

All configuration source files live under `src/attune/config/`.
