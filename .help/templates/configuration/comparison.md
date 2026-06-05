---
type: comparison
name: configuration-comparison
feature: configuration
depth: comparison
generated_at: 2026-06-04T23:45:26.726411+00:00
source_hash: b67c4428689dde6c18aca17808e3037eded03448162cc3406741340bbe33b804
status: generated
---

# Comparison: Configuration Approaches

## Context

Attune exposes two distinct configuration systems side by side:

- **`UnifiedConfig` / `ConfigLoader`** — a file-backed, section-structured config used by the agent and workflow layer
- **`EmpathyXMLConfig`** — a legacy global-singleton config loaded from `.attune/config.json` or environment variables

Understanding which system owns what prevents subtle conflicts, especially when environment variable overrides are involved.

## Feature comparison

| Capability | `UnifiedConfig` + `ConfigLoader` | `EmpathyXMLConfig` |
|---|---|---|
| **Primary entry point** | `load_unified_config()` / `get_loader()` | `get_config()` / `set_config()` |
| **File format** | YAML or JSON (auto-discovered) | JSON only (`.attune/config.json`) |
| **Search path** | `./attune.config.json`, `~/.attune/config.json`, `~/.config/attune/config.json` | Fixed: `.attune/config.json` |
| **Environment overrides** | `ConfigLoader.apply_env_overrides()` reads `ATTUNE_` prefix | `EmpathyXMLConfig.from_env()` reads `ATTUNE_` prefix |
| **Env variable lookup** | `get_attune_env()` — checks `ATTUNE_` first, falls back to `EMPATHY_` | Same fallback via `from_env()` |
| **Structured sections** | Yes — `AnalysisConfig`, `AuthConfig`, `EnvironmentConfig`, `PersistenceConfig`, `RoutingConfig`, `TelemetryConfig`, `WorkflowConfig` | No — flat sub-objects: `XMLConfig`, `OptimizationConfig`, `AdaptiveConfig`, `I18nConfig`, `MetricsConfig` |
| **Validation** | `validate_config(config)` returns `list[ValidationError]` | None exposed in public API |
| **Agent/workflow integration** | Direct — `UnifiedAgentConfig`, `BookProductionConfig`, `WorkflowMode` all consume `UnifiedConfig` | Indirect — agents read global singleton via `get_config()` |
| **Serialization** | `UnifiedConfig.to_dict()` / `from_dict()` on every section | `save_to_file()` / `load_from_file()` on the top-level object |
| **Save location control** | `save_unified_config(config, path)` accepts an explicit path | `save_to_file(config_file=...)` accepts an explicit path |
| **Global singleton** | No — instantiate `ConfigLoader` or call `load_unified_config()` | Yes — `get_config()` / `set_config()` manage a module-level instance |
| **Key–value access** | `UnifiedConfig.get_value(key)` / `set_value(key, value)` / `get_all_keys()` | Not available |

## Tradeoffs

**`UnifiedConfig` + `ConfigLoader` is the right default.** It is the system that agent classes, workflow modes, and book-production pipelines are built on. `ConfigLoader.apply_env_overrides()` gives you a single, explicit place where environment variables win, and `validate_config()` surfaces `ValidationError` objects at load time rather than at the point of use. The three-path discovery order (`./attune.config.json` → `~/.attune/config.json` → `~/.config/attune/config.json`) means the same code works across developer workstations, CI, and production without any changes.

**`EmpathyXMLConfig` is a narrower, legacy surface.** Its global-singleton pattern (`get_config()` / `set_config()`) is convenient for code that predates the unified system but makes testing harder — replacing the singleton in one test can affect another. It has no built-in validation pass, so missing or malformed values surface as runtime errors rather than startup errors. Use it only when integrating with existing code that already calls `get_config()`.

One practical difference worth noting: `get_attune_env()` checks `ATTUNE_` first and then falls back to `EMPATHY_` for backward compatibility. Both systems share this fallback, so a variable set as `EMPATHY_FOO` is visible through either path. `iter_attune_env_prefix(prefix, suffix)` lets you enumerate all variables matching `ATTUNE_{prefix}*{suffix}`, which is useful when the unified config section names map directly to env var prefixes.

## Use X when…

**Use `UnifiedConfig` + `ConfigLoader` when:**
- You are writing new agent, workflow, or book-production code — `UnifiedAgentConfig` and `BookProductionConfig` depend on it directly
- You need structured, validated sections (`AuthConfig`, `TelemetryConfig`, `PersistenceConfig`, etc.) with `validate_config()` catching problems at startup
- You want explicit, path-controlled saves via `save_unified_config(config, path)`
- You are writing tests that must swap config without global state leaking between cases

**Use `EmpathyXMLConfig` when:**
- You are maintaining or extending existing code that already calls `get_config()` / `set_config()`
- You need to construct config entirely from environment variables via `EmpathyXMLConfig.from_env()` with no file on disk
- The sub-objects you need (`OptimizationConfig`, `AdaptiveConfig`, `I18nConfig`, `MetricsConfig`) are only modeled in this system

**Do not use either system directly when:**
- You need runtime behavior that no public method exposes — extend the relevant section class rather than patching internals
- You are writing a throwaway script that reads one or two values — call `get_attune_env(name, default)` directly instead of loading a full config object
