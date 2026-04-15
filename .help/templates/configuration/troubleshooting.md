---
type: troubleshooting
feature: configuration
depth: troubleshooting
generated_at: 2026-04-14T15:30:51.055336+00:00
source_hash: 4aba109a0dfc8d51fc39c5be662b4c0ce340e3fe680c780d425e04060f8e199d
status: generated
---

# Troubleshoot configuration

## Before you start

Configuration issues in Attune AI typically involve loading unified agent configurations, environment variable resolution, or compatibility between ATTUNE_ and EMPATHY_ prefixed variables.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `AgentOperationError` during config load | Validate the config file exists at the expected path and check the operation context in the error message |
| Environment variables not recognized | Confirm variable names use `ATTUNE_` prefix or legacy `EMPATHY_` fallback format |
| Config file not found | Verify the search order: `./attune.config.json`, `~/.attune/config.json`, `~/.config/attune/config.json` |
| Model/provider validation errors | Check that `Provider` and `ModelTier` values match the enumerated options |
| Workflow mode conflicts | Ensure `WorkflowMode` setting is compatible with your agent type |

## Step-by-step diagnosis

1. **Test configuration loading in isolation.**
   Create a minimal test to load your configuration:
   ```python
   from attune.config.loader import load_unified_config
   config = load_unified_config()  # Uses default search paths
   ```

2. **Check configuration file discovery.**
   Verify which config file is being loaded:
   ```python
   from attune.config.loader import ConfigLoader
   loader = ConfigLoader()
   path = loader.discover_config_path()
   print(f"Using config: {path}")
   ```

3. **Validate environment variable resolution.**
   Test the environment variable compatibility layer:
   ```python
   from attune.config.env_compat import get_attune_env
   # Check specific variables
   api_key = get_attune_env("API_KEY")  # Checks ATTUNE_API_KEY then EMPATHY_API_KEY
   ```

4. **Run configuration validation.**
   Use the built-in validation to catch schema issues:
   ```python
   from attune.config.loader import validate_config
   errors = validate_config(config)
   for error in errors:
       print(f"Validation error: {error}")
   ```

5. **Enable debug logging.**
   Set logging level to DEBUG to see configuration loading details:
   ```python
   import logging
   logging.getLogger('attune.config').setLevel(logging.DEBUG)
   ```

## Common fixes

- **Missing config file:** Create a config file at one of the search paths. Use `ConfigLoader.get_default_config_path()` to find the preferred location.

- **Environment variable not found:** Check both prefixes. If you set `EMPATHY_MODEL_TIER=premium`, it should work, but `ATTUNE_MODEL_TIER=premium` takes precedence.

- **Invalid enum values:** For `Provider`, `ModelTier`, or `WorkflowMode`, check the source code for valid options. Common values include `Provider.OPENAI` and `ModelTier.PREMIUM`.

- **Config validation errors:** Run `validate_config()` and fix schema violations. Required fields for `UnifiedAgentConfig` include provider and model configuration.

- **Book production compatibility:** If using legacy book production agents, call `config.for_book_production()` to get a compatible `BookProductionConfig` instance.

- **Redis/MemDocs connection issues:** Verify your `RedisConfig` and `MemDocsConfig` sections have correct connection parameters for external services.

## Source files

- `src/attune/config/**`

**Tags:** `config`, `settings`
