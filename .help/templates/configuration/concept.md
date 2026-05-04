---
type: concept
feature: configuration
depth: concept
generated_at: 2026-05-04T02:40:39.296563+00:00
source_hash: b67c4428689dde6c18aca17808e3037eded03448162cc3406741340bbe33b804
status: generated
---

# Configuration

Configuration is the centralized system that manages settings, credentials, and runtime parameters for Attune AI agents across different environments and deployment contexts.

## Core components

The configuration system provides three layers of functionality:

**Environment integration** handles the bridge between code and runtime environments. The `get_attune_env()` function checks for `ATTUNE_` prefixed variables first, then falls back to legacy `EMPATHY_` variables for backward compatibility. This dual-prefix approach lets you migrate environments gradually without breaking existing deployments.

**Unified configuration model** centers on `UnifiedAgentConfig`, which consolidates settings for all agent types. This class handles model selection through `get_model_id()`, validates role assignments with `normalize_role()`, and provides specialized configurations like `for_book_production()` that return tailored config objects for specific workflows.

**File and environment loading** happens through `ConfigLoader`, which searches standard paths (`./attune.config.json`, `~/.attune/config.json`, `~/.config/attune/config.json`) and applies environment variable overrides automatically. The loader ensures that environment variables always take precedence over file-based settings.

## Configuration types

Different parts of the system use specialized config classes:

| Config class | Purpose | Key settings |
|--------------|---------|--------------|
| `UnifiedAgentConfig` | Core agent behavior | Model tier, provider, role, timeout |
| `BookProductionConfig` | Book generation workflows | Model compatibility properties, retry logic |
| `MemDocsConfig` | Pattern storage integration | Memory document handling |
| `RedisConfig` | State management | Redis connection parameters |
| `WorkflowConfig` | Agent orchestration | Workflow modes and execution settings |

## Environment variable patterns

The system follows a predictable naming convention for environment variables:

- `ATTUNE_MODEL_TIER` sets the cost optimization level (`ModelTier` enum)
- `ATTUNE_PROVIDER` selects the LLM provider (`Provider` enum)
- `ATTUNE_WORKFLOW_MODE` configures execution behavior (`WorkflowMode` enum)
- `ATTUNE_*_TIMEOUT`, `ATTUNE_*_RETRIES` control resilience settings

You can enumerate all variables with a specific pattern using `iter_attune_env_prefix()`, which yields matching environment variables for bulk configuration scenarios.

## Configuration lifecycle

Configuration loading follows a predictable sequence: the `ConfigLoader` discovers the config file location, loads base settings from JSON, then applies environment variable overrides using `apply_env_overrides()`. The resulting `UnifiedConfig` object gets validated through `validate_config()` before use.

Global access happens through `get_config()` and `set_config()` functions that maintain a singleton instance, while `load_unified_config()` and `save_unified_config()` provide file-based operations for configuration management tools.
