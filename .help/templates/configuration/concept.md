---
type: concept
feature: configuration
depth: concept
generated_at: 2026-04-14T15:29:31.589316+00:00
source_hash: 4aba109a0dfc8d51fc39c5be662b4c0ce340e3fe680c780d425e04060f8e199d
status: generated
---

# Configuration

Configuration provides a unified system for managing settings across all Attune AI agents, with automatic environment variable integration and backward compatibility.

## Core components

The configuration system centers around three key pieces:

- **`UnifiedAgentConfig`** — The main configuration model that all agents inherit from, providing consistent settings like model selection, timeouts, and retry behavior
- **`ConfigLoader`** — Handles loading configuration from files (JSON/YAML) with automatic discovery across standard locations like `~/.attune/config.json`
- **Environment variable layer** — Automatically applies `ATTUNE_*` environment variables as overrides, with fallback support for legacy `EMPATHY_*` prefixes

## Configuration types

Different agent types use specialized configuration classes that extend the unified model:

- **`BookProductionConfig`** — Settings for book production workflows, with backward-compatible properties that map to the unified model
- **`WorkflowConfig`** — Configuration for multi-step agent workflows
- **`MemDocsConfig`** — Settings for pattern storage integration
- **`RedisConfig`** — Redis connection and state management settings

## Model and provider settings

The system includes enums that standardize key choices:

- **`Provider`** — Supported LLM providers (OpenAI, Anthropic, etc.)
- **`ModelTier`** — Cost optimization tiers that group models by expense
- **`WorkflowMode`** — Execution modes for complex workflows

## File discovery and environment integration

When you load configuration, the system searches these locations in order:
1. `./attune.config.json` (project-specific)
2. `~/.attune/config.json` (user-specific)
3. `~/.config/attune/config.json` (XDG standard)

Environment variables automatically override file settings using the pattern `ATTUNE_{SECTION}_{SETTING}`, like `ATTUNE_MODEL_PROVIDER=openai` or `ATTUNE_WORKFLOW_TIMEOUT=300`.
