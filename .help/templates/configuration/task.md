---
type: task
name: configuration-task
feature: configuration
depth: task
generated_at: 2026-06-04T23:45:26.696710+00:00
source_hash: b67c4428689dde6c18aca17808e3037eded03448162cc3406741340bbe33b804
status: generated
---

# Work with configuration

Use Attune's configuration system when you need to load, validate, override, or persist settings across environments without changing your source code.

## Prerequisites

- Access to the project source code under `src/attune/config/`
- Python environment with the Attune package installed

## Load configuration

1. **Load the unified config from disk.** Call `load_unified_config()` with an optional path. If you omit the path, the loader searches `./attune.config.json`, `~/.attune/config.json`, and `~/.config/attune/config.json` in order.

   ```python
   from attune.config.loader import load_unified_config

   config = load_unified_config()          # auto-discover
   config = load_unified_config("my.json") # explicit path
   ```

2. **Apply environment variable overrides.** Call `ConfigLoader.apply_env_overrides()` to layer `ATTUNE_`-prefixed environment variables on top of the loaded config. This happens automatically when you use `load_unified_config()`, but you can call it explicitly after manual edits.

   ```python
   from attune.config.loader import get_loader

   loader = get_loader()
   config = loader.get_config()  # loads and applies env overrides
   ```

3. **Read individual environment variables.** Use `get_attune_env()` when you need a single value. It checks `ATTUNE_<NAME>` first, then falls back to `EMPATHY_<NAME>`.

   ```python
   from attune.config.env_compat import get_attune_env

   api_url = get_attune_env("API_URL", default="http://localhost")
   ```

## Read and write config values

1. **Get a value by key.** Call `UnifiedConfig.get_value()` with the dot-separated key you want to inspect.

   ```python
   value = config.get_value("auth.token")
   ```

2. **List all available keys.** Call `config.get_all_keys()` to see every key the loaded config exposes.

3. **Set a value.** Call `config.set_value()` to update a key in memory, then save the result.

   ```python
   config.set_value("telemetry.enabled", False)
   ```

4. **Save the updated config to disk.** Call `save_unified_config()`. The function returns the `Path` it wrote to.

   ```python
   from attune.config.loader import save_unified_config

   written_path = save_unified_config(config)
   print(f"Saved to {written_path}")
   ```

## Validate configuration

1. **Run validation against the loaded config.** Call `validate_config()` and inspect the returned list. An empty list means validation passed.

   ```python
   from attune.config.validation import validate_config

   errors = validate_config(config)
   if errors:
       for err in errors:
           print(err)
   ```

2. **Fix any reported errors** before saving or passing the config to other components. Each `ValidationError` describes the field and constraint that failed.

## Configure agents and book production

1. **Build a `UnifiedAgentConfig`.** Set the `role`, `provider` (`Provider`), and `model_tier` (`ModelTier`) fields. Call `normalize_role()` to canonicalize the role string before use.

2. **Derive a `BookProductionConfig`.** Call `UnifiedAgentConfig.for_book_production()` to get a pre-populated config with `model`, `max_tokens`, `temperature`, `timeout`, `retry_attempts`, and `retry_delay` properties ready for agent use.

   ```python
   from attune.config.agent_config import UnifiedAgentConfig, Provider, ModelTier

   agent_cfg = UnifiedAgentConfig(role="editor", provider=Provider.OPENAI, model_tier=ModelTier.STANDARD)
   book_cfg = agent_cfg.for_book_production()
   print(book_cfg.model, book_cfg.max_tokens)
   ```

## Manage the global EmpathyXMLConfig

1. **Load from a JSON file.** Call `EmpathyXMLConfig.load_from_file()`. The default path is `.attune/config.json`.

   ```python
   from attune.config.xml_config import EmpathyXMLConfig

   cfg = EmpathyXMLConfig.load_from_file()
   ```

2. **Load from environment variables.** Call `EmpathyXMLConfig.from_env()` when no config file is present.

3. **Set the global instance.** Call `set_config()` so that other components that call `get_config()` receive your updated config.

   ```python
   from attune.config import set_config
   set_config(cfg)
   ```

4. **Save changes back to disk.** Call `cfg.save_to_file()` with an optional path.

## Verify the task succeeded

Run the configuration-related tests to confirm your changes load, validate, and save correctly:

```bash
pytest -k "configuration"
```

A passing test run with no `ValidationError` objects returned by `validate_config()` confirms the configuration is well-formed. If you called `save_unified_config()`, check that the returned `Path` exists on disk and contains your updated values.
