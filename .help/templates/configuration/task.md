---
type: task
feature: configuration
depth: task
generated_at: 2026-04-14T15:29:44.272903+00:00
source_hash: 4aba109a0dfc8d51fc39c5be662b4c0ce340e3fe680c780d425e04060f8e199d
status: generated
---

# Work with configuration

Use Attune's configuration system when you need to manage application settings, environment variables, or agent parameters across different execution contexts.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/config/**

## Load configuration

1. **Import the configuration loader:**
   ```python
   from attune.config import load_unified_config, get_loader
   ```

2. **Load configuration from default paths:**
   ```python
   config = load_unified_config()
   ```
   This searches for config files in `./attune.config.json`, `~/.attune/config.json`, and `~/.config/attune/config.json`.

3. **Load configuration from a specific path:**
   ```python
   config = load_unified_config("/path/to/your/config.json")
   ```

4. **Verify the configuration loaded correctly:**
   Check that `config` contains your expected settings and no validation errors occur.

## Set up environment variables

1. **Use the ATTUNE_ prefix for new variables:**
   ```bash
   export ATTUNE_MODEL_TIER=premium
   export ATTUNE_PROVIDER=openai
   ```

2. **Access environment variables in code:**
   ```python
   from attune.config import get_attune_env

   model_tier = get_attune_env("MODEL_TIER", "basic")
   ```

3. **Apply environment overrides to loaded config:**
   ```python
   from attune.config.loader import ConfigLoader

   loader = ConfigLoader()
   config = loader.load()
   config = loader.apply_env_overrides(config)
   ```

4. **Verify environment variables are accessible:**
   Print the variable value to confirm it was read correctly.

## Configure agents

1. **Create a unified agent configuration:**
   ```python
   from attune.config import UnifiedAgentConfig, ModelTier, Provider

   agent_config = UnifiedAgentConfig(
       model_tier=ModelTier.PREMIUM,
       provider=Provider.OPENAI,
       role="assistant",
       max_tokens=4000
   )
   ```

2. **Convert to book production format:**
   ```python
   book_config = agent_config.for_book_production()
   model_id = book_config.model  # Access with backward compatibility
   ```

3. **Validate the agent configuration:**
   ```python
   from attune.config import validate_config

   errors = validate_config(config)
   if errors:
       for error in errors:
           print(f"Validation error: {error}")
   ```

4. **Confirm the agent accepts your configuration:**
   Initialize your agent with the config and verify it starts without errors.

## Save configuration

1. **Create or modify a configuration object:**
   ```python
   from attune.config import UnifiedConfig

   # Modify existing config or create new one
   config.agent.model_tier = ModelTier.BASIC
   ```

2. **Save to the default location:**
   ```python
   from attune.config import save_unified_config

   saved_path = save_unified_config(config)
   print(f"Config saved to: {saved_path}")
   ```

3. **Save to a specific location:**
   ```python
   saved_path = save_unified_config(config, "/custom/path/config.json")
   ```

4. **Verify the file was written:**
   Check that the saved file exists and contains your expected configuration values.

## Key files

- `src/attune/config/loader.py` — Core configuration loading and saving
- `src/attune/config/env_compat.py` — Environment variable handling
- `src/attune/config/unified.py` — Unified configuration data models
- `src/attune/config/validation.py` — Configuration validation

## Run tests

Target configuration-related tests to verify your changes:
```bash
pytest -k "configuration"
```
