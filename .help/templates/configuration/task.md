---
type: task
feature: configuration
depth: task
generated_at: 2026-05-04T02:40:55.356121+00:00
source_hash: b67c4428689dde6c18aca17808e3037eded03448162cc3406741340bbe33b804
status: generated
---

# Work with configuration

Use configuration management when you need to load settings, access environment variables, or modify how Attune AI handles configuration across different deployment environments.

## Prerequisites

- Access to the project source code
- Understanding of the Attune AI configuration system structure

## Examine the configuration system

1. **Review the unified configuration model.**
   Start with `UnifiedAgentConfig` in `src/attune/config/` to understand the main configuration structure:
   ```python
   from attune.config import load_unified_config
   config = load_unified_config()
   print(config.model_dump())
   ```

2. **Check current environment variables.**
   Use the environment compatibility layer to see what's loaded:
   ```python
   from attune.config.env_compat import get_attune_env, iter_attune_env_prefix

   # Check specific variable
   api_key = get_attune_env("API_KEY")

   # List all ATTUNE_MODEL_* variables
   for name, value in iter_attune_env_prefix("MODEL"):
       print(f"ATTUNE_MODEL_{name} = {value}")
   ```

## Load and modify configuration

3. **Load configuration from default sources.**
   The loader checks multiple paths automatically:
   ```python
   from attune.config import get_loader

   loader = get_loader()
   config = loader.load()
   ```

4. **Save configuration changes.**
   Modify settings and persist them:
   ```python
   config.model_tier = ModelTier.PREMIUM
   config.timeout = 30

   saved_path = loader.save(config)
   print(f"Configuration saved to {saved_path}")
   ```

5. **Apply environment overrides.**
   Environment variables take precedence over file settings:
   ```python
   config = loader.load()
   config_with_env = loader.apply_env_overrides(config)
   ```

## Validate configuration

6. **Check for configuration errors.**
   Validate before using the configuration:
   ```python
   from attune.config import validate_config

   errors = validate_config(config)
   if errors:
       for error in errors:
           print(f"Config error: {error}")
   ```

7. **Test your changes.**
   Run configuration-specific tests:
   ```bash
   pytest -k "config" -v
   ```

## Success criteria

Your configuration changes work correctly when:
- `load_unified_config()` returns valid configuration without errors
- Environment variable overrides apply as expected
- Configuration validates successfully with `validate_config()`
- Related tests pass without regressions
