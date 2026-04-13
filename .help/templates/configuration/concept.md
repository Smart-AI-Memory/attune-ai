---
feature: configuration
depth: concept
generated_at: 2026-04-13T17:03:44.253844+00:00
source_hash: 4aba109a0dfc8d51fc39c5be662b4c0ce340e3fe680c780d425e04060f8e199d
status: generated
---

# Configuration

## How it works

Centralized configuration management system for Attune AI agents and workflows.

The main building blocks are:

- **`ModelTier`** — Cost optimization levels for LLM models.
- **`Provider`** — Available LLM provider options.
- **`WorkflowMode`** — Agent workflow execution strategies.
- **`UnifiedAgentConfig`** — Centralized configuration model for all agents.
- **`ConfigLoader`** — Configuration file loading, saving, and validation.

Under the hood, this feature spans 15 source
files covering:

- Environment variable compatibility with ATTUNE_ and EMPATHY_ prefixes
- Redis and MemDocs integration configuration
- Book production workflow settings
- Global configuration state management

## What connects to it

This feature relates to: config, settings.

Other parts of the codebase interact with
configuration through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `get_config()` | Get global configuration instance | `src/attune/config/__init__.py` |
| `load_unified_config()` | Load unified configuration from file | `src/attune/config/__init__.py` |
| `get_attune_env()` | Get environment variables with prefix fallback | `src/attune/config/env.py` |
| `UnifiedAgentConfig` | Unified configuration model for all agents | `src/attune/config/agent_config.py` |
| `WorkflowConfig` | Configuration for agent workflows | `src/attune/config/agent_config.py` |
