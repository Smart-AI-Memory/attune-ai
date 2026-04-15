---
type: error
feature: configuration
depth: error
generated_at: 2026-04-14T15:30:20.822597+00:00
source_hash: 4aba109a0dfc8d51fc39c5be662b4c0ce340e3fe680c780d425e04060f8e199d
status: generated
---

# Configuration errors

Failures during configuration loading, validation, and environment variable resolution in Attune AI.

## Common error signatures

- `AgentOperationError` — Error during agent operation with context, wrapping the original cause
- `ValidationError` — Configuration validation failures from malformed or missing required fields
- `FileNotFoundError` — Config file not found at expected paths (`./attune.config.json`, `~/.attune/config.json`, `~/.config/attune/config.json`)
- `JSONDecodeError` — Malformed JSON in configuration files
- `AttributeError` — Missing configuration properties when accessing `model`, `max_tokens`, `temperature`, or other required fields
- `KeyError` — Missing environment variables or configuration sections

## Where errors originate

Configuration errors typically start in these key functions:

- `ConfigLoader.load()` — Configuration file loading and parsing failures
- `ConfigLoader.save()` — File write permission or path creation issues
- `validate_config()` — Schema validation errors for configuration objects
- `get_attune_env()` — Environment variable resolution when neither `ATTUNE_` nor `EMPATHY_` variants exist
- `UnifiedAgentConfig.get_model_id()` — Model configuration resolution failures
- `BookProductionConfig` property accessors — Missing or invalid model configuration values

## How to diagnose

1. **Check configuration file paths.** Run `ConfigLoader.discover_config_path()` to see if your config file exists at the expected locations. If `None` is returned, the loader can't find a configuration file.

2. **Validate environment variables.** Use `get_attune_env()` with your variable name to confirm environment variable resolution. The function checks `ATTUNE_` prefixed variables first, then falls back to `EMPATHY_` prefixed ones.

3. **Test configuration loading directly.** Call `load_unified_config()` in isolation to separate file loading issues from configuration usage problems. JSON parsing errors will surface immediately.

4. **Run configuration validation.** Use `validate_config()` on your loaded configuration object to catch schema violations before they cause runtime failures in agent operations.

5. **Check agent configuration properties.** If using `BookProductionConfig`, verify that accessing `model`, `max_tokens`, and other properties doesn't raise `AttributeError` — this indicates missing required configuration sections.

## Source files

- `src/attune/config/**`

**Tags:** `config`, `settings`
