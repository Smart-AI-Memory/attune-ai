---
type: warning
feature: configuration
depth: warning
generated_at: 2026-04-14T15:30:33.691904+00:00
source_hash: 4aba109a0dfc8d51fc39c5be662b4c0ce340e3fe680c780d425e04060f8e199d
status: generated
---

# Configuration cautions

## What to watch for

Configuration management in Attune AI involves multiple layers of settings, environment variables, and global state that can interact in unexpected ways.

## Risk areas

### Environment variable precedence conflicts

The `get_attune_env()` function checks `ATTUNE_` prefixed variables first, then falls back to `EMPATHY_` prefixed ones. This dual-prefix system can mask configuration issues when both prefixes are set to different values. You might think you're using the `EMPATHY_` value when `ATTUNE_` is actually taking precedence.

### Global configuration state mutations

The global `ConfigLoader` instance returned by `get_loader()` maintains state across your application. If multiple parts of your code call `load()` or modify the configuration path, later calls may use a different configuration than expected. This is especially problematic in test suites where configuration changes can leak between tests.

### Configuration file discovery ambiguity

The `discover_config_path()` method searches multiple locations (`./attune.config.json`, `~/.attune/config.json`, `~/.config/attune/config.json`) and returns the first match. If you have configuration files in multiple locations, you may not be loading the file you expect, particularly when running code from different working directories.

### Backward compatibility property access

`BookProductionConfig` exposes properties like `model`, `max_tokens`, and `temperature` for backward compatibility. These properties may return different values than direct field access if the underlying configuration structure has changed, creating subtle inconsistencies in agent behavior.

### Environment override timing

The `apply_env_overrides()` function modifies configuration after the base config is loaded. If you cache configuration values before applying environment overrides, those cached values won't reflect the environment variable changes.

## How to avoid problems

**Pin your configuration path explicitly** instead of relying on discovery. Pass a specific path to `ConfigLoader()` rather than letting it search multiple locations.

**Isolate configuration in tests** by creating fresh `ConfigLoader` instances for each test case rather than using the global instance from `get_loader()`.

**Validate environment variable conflicts** by checking both `ATTUNE_` and `EMPATHY_` prefixes during deployment. Set up monitoring to alert when both prefixes exist for the same configuration key.

**Load configuration once per process** and pass it down rather than calling `load_unified_config()` from multiple places. This prevents inconsistent configuration states within the same application run.

**Use `validate_config()` after any configuration changes** to catch structural issues before they affect agent operations.
