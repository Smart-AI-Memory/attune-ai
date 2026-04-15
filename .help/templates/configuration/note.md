---
type: note
feature: configuration
depth: note
generated_at: 2026-04-14T15:31:37.439004+00:00
source_hash: 4aba109a0dfc8d51fc39c5be662b4c0ce340e3fe680c780d425e04060f8e199d
status: generated
---

# Note: configuration

## Context

Attune AI's configuration system provides unified settings management across all agents and workflows, with support for multiple file formats and environment variable overrides.

## Configuration architecture

The configuration system centers on the `UnifiedAgentConfig` class, which normalizes settings for all agent types. The `ConfigLoader` class handles file discovery, loading, and saving, while maintaining backward compatibility with legacy configuration formats.

Configuration files are discovered automatically using a search path hierarchy:
1. `./attune.config.json` (project-local)
2. `~/.attune/config.json` (user-specific)
3. `~/.config/attune/config.json` (XDG standard)

## Environment variable compatibility

The system maintains compatibility with legacy `EMPATHY_` environment variables while transitioning to the `ATTUNE_` prefix. The `get_attune_env()` function checks for `ATTUNE_` variables first, then falls back to `EMPATHY_` equivalents.

## Agent specialization

While `UnifiedAgentConfig` provides the base configuration model, specialized configurations like `BookProductionConfig` extend it with agent-specific settings. The `for_book_production()` method creates these specialized configurations while preserving the unified structure.

## Workflow integration

The `WorkflowConfig` class manages agent workflow execution, supporting different modes through the `WorkflowMode` enum. This allows workflows to run in development, production, or testing configurations without code changes.

## Source files

Configuration management spans multiple modules in `src/attune/config/`, including agent configurations, environment compatibility layers, and the core configuration loader.

**Tags:** `config`, `settings`
