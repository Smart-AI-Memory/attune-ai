---
type: troubleshooting
name: configuration-troubleshooting
feature: configuration
depth: troubleshooting
generated_at: 2026-06-04T23:45:26.714110+00:00
source_hash: b67c4428689dde6c18aca17808e3037eded03448162cc3406741340bbe33b804
status: generated
---

# Troubleshoot configuration

## Symptom table

| If you observe | Check |
|----------------|-------|
| `AgentOperationError` raised during agent startup | The `operation` and `cause` fields on the exception — they name the failing step and its root cause |
| Config values not reflecting environment variables | Whether you set `ATTUNE_` or `EMPATHY_` prefixes — `get_attune_env()` checks `ATTUNE_` first, then falls back to `EMPATHY_` |
| `load_unified_config()` returns unexpected values | Whether a config file exists at one of the three search paths: `./attune.config.json`, `~/.attune/config.json`, or `~/.config/attune/config.json` |
| `validate_config()` returns a non-empty list | Each `ValidationError` in the list — check `section_name` to isolate which config section is invalid |
| `EmpathyXMLConfig.load_from_file()` fails | Whether `.attune/config.json` exists and is valid JSON; it's the default path |
| Config changes not persisting | Whether you called `save_unified_config()` and that it wrote to the expected path (it returns the `Path` it saved to) |
| `BookProductionConfig` properties returning wrong values | The underlying `UnifiedAgentConfig` — call `get_model_id()` directly to verify the model resolved correctly |

## Diagnose the problem

### 1. Check which config file is being loaded

`ConfigLoader.discover_config_path()` searches the three known locations in order. Confirm which file it finds — or whether it finds none — before assuming your edits took effect:

```python
from attune.config.loader import ConfigLoader

path = ConfigLoader.discover_config_path()
print(path)  # None means no file was found; defaults apply
```

If `path` is `None`, call `ConfigLoader.get_default_config_path()` to see where a new file would be written.

### 2. Verify environment variable resolution

`get_attune_env()` checks `ATTUNE_<name>` first and falls back to `EMPATHY_<name>`. If a value is not resolving as expected, print both candidates:

```python
import os
name = "MY_VAR"
print(os.environ.get(f"ATTUNE_{name}"))
print(os.environ.get(f"EMPATHY_{name}"))
```

To inspect all variables under a prefix — for example, all routing overrides — use `iter_attune_env_prefix()`:

```python
from attune.config.env_compat import iter_attune_env_prefix

for middle, value in iter_attune_env_prefix("ROUTING_"):
    print(middle, value)
```

### 3. Run validation and read every error

Call `validate_config()` on your loaded config and print the full list of `ValidationError` objects. Each error names the offending section:

```python
from attune.config.loader import load_unified_config
from attune.config.validation import validate_config

config = load_unified_config()
errors = validate_config(config)
for err in errors:
    print(err)
```

Zero errors here rules out malformed config as the cause.

### 4. Confirm environment overrides are applied

`ConfigLoader.apply_env_overrides()` is a separate step from loading. If you load a config manually and skip this call, environment variables will not be reflected:

```python
from attune.config.loader import get_loader

loader = get_loader()
config = loader.load()
config = loader.apply_env_overrides(config)
```

Use `load_unified_config()` instead of `loader.load()` directly if you want both steps handled for you.

### 5. Inspect individual values and all known keys

Use `UnifiedConfig.get_all_keys()` to enumerate every key the config object knows about, then `get_value()` to spot-check suspicious ones:

```python
config = load_unified_config()
for key in config.get_all_keys():
    print(key, config.get_value(key))
```

### 6. Run the configuration tests

```bash
pytest -k "config" -v
```

A failing test that exercises your code path is the fastest way to isolate whether the problem is in the config layer itself or in how it is called.

## Common fixes

**Missing or wrong config file path**
Pass the path explicitly to avoid relying on discovery:

```python
from attune.config.loader import load_unified_config
config = load_unified_config(path="/absolute/path/to/attune.config.json")
```

**Environment variable not picked up**
Prefix your variable with `ATTUNE_` (preferred) or `EMPATHY_` (legacy fallback). Both are checked by `get_attune_env()`. Variables without either prefix are invisible to the config system.

**Config saved to the wrong location**
`save_unified_config()` returns the `Path` it actually wrote to. Capture and log it:

```python
from attune.config.loader import save_unified_config
saved_path = save_unified_config(config)
print(f"Saved to: {saved_path}")
```

**`EmpathyXMLConfig` not reflecting code changes**
`get_config()` returns a global singleton. If you need to replace it in tests or after a reload, call `set_config()` explicitly with a new `EmpathyXMLConfig` instance. Otherwise the old instance persists for the lifetime of the process.

**`BookProductionConfig` properties returning stale values**
`BookProductionConfig` exposes `model`, `max_tokens`, `temperature`, `timeout`, `retry_attempts`, and `retry_delay` as computed properties derived from `UnifiedAgentConfig`. If any of these look wrong, inspect the parent config by calling `UnifiedAgentConfig.get_model_id()` and checking the `ModelTier` and `Provider` fields directly.

**Validation errors in a specific section**
Each config section (`AuthConfig`, `RoutingConfig`, `TelemetryConfig`, `AnalysisConfig`, `PersistenceConfig`, `EnvironmentConfig`, `WorkflowConfig`) exposes `to_dict()` and `from_dict()`. Round-trip the failing section to confirm it survives serialization:

```python
section_dict = config_section.to_dict()
restored = type(config_section).from_dict(section_dict)
```

A mismatch between `section_dict` and the restored object identifies which field is not serializing correctly.

**YAML not available**
`YAML_AVAILABLE` is a module-level flag in `config`. If it is `False`, YAML-format config files will not load. Install PyYAML:

```bash
pip install pyyaml
```

## Source files

- `src/attune/config/**`

**Tags:** `config`, `settings`
