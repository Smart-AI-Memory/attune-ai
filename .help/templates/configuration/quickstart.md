---
type: quickstart
name: configuration-quickstart
feature: configuration
depth: quickstart
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 5e48805be1a999be45deb9a9c24e4965ca3ad0e741320a5c68a4675f40612ac8
status: generated
---

# Quickstart: Attune Configuration

Load your first `UnifiedConfig` object and confirm it reads correctly:

```python
from attune.config.loader import load_unified_config

config = load_unified_config()
print(config.to_dict())
```

If a config file exists at one of the default search paths (`./attune.config.json`, `~/.attune/config.json`, or `~/.config/attune/config.json`), you'll see its contents printed as a dictionary. If no file is found, you'll see the defaults.

## Prerequisites

- The package is installed in your local environment
- Optionally, a config file exists at one of the `CONFIG_SEARCH_PATHS` locations

## Step 1: Validate the loaded config

Pass the config object to `validate_config` to catch any missing or malformed values before they cause runtime errors:

```python
from attune.config.loader import load_unified_config
from attune.config.validation import validate_config

config = load_unified_config()
errors = validate_config(config)

if errors:
    for e in errors:
        print(e)
else:
    print("Config is valid.")
```

Expected output when config is valid:

```
Config is valid.
```

## Step 2: Override a value and save

Use `set_value` to change a config value in memory, then write it back to disk with `save_unified_config`:

```python
from attune.config.loader import load_unified_config, save_unified_config

config = load_unified_config()
config.set_value("telemetry.enabled", False)

saved_path = save_unified_config(config)
print(f"Saved to: {saved_path}")
```

Expected output:

```
Saved to: /home/you/.attune/config.json
```

## Step 3: Apply environment variable overrides

`ATTUNE_` environment variables override file-based config at load time. To apply them explicitly to an existing config object, call `apply_env_overrides`:

```python
from attune.config.loader import load_unified_config, ConfigLoader

config = load_unified_config()
config = ConfigLoader.apply_env_overrides(config)
print(config.get_value("telemetry.enabled"))
```

Set `ATTUNE_TELEMETRY_ENABLED=false` in your shell before running to see the override take effect.

## Step 4: Read a value and check all available keys

```python
from attune.config.loader import load_unified_config

config = load_unified_config()
print(config.get_all_keys())
print(config.get_value("telemetry.enabled"))
```

This prints every key the config object knows about, then the current value of one of them — confirming the config is fully loaded and accessible.

---

**Next:** Read the `UnifiedAgentConfig` reference to learn how agent-specific settings — including `ModelTier`, `Provider`, and `WorkflowMode` — layer on top of `UnifiedConfig`.
