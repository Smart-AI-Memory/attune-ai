---
feature: configuration
depth: concept
generated_at: 2026-04-06T04:36:26.397569+00:00
source_hash: 6be742830b8d72209e378e70916c649d55dd40a3afdfa434cf328395a1bc4ee3
status: generated
---

# Configuration

## How it works

The configuration system manages settings and options for all Attune AI agents with environment variable support and unified configuration models.

The main building blocks are:

- **`ModelTier`** — Defines cost optimization levels for different model usage scenarios.
- **`Provider`** — Specifies which LLM provider to use for agent operations.
- **`WorkflowMode`** — Controls how agent workflows execute (sequential, parallel, etc.).
- **`AgentOperationError`** — Provides detailed error context when agent operations fail.
- **`UnifiedAgentConfig`** — Contains all configuration options for agents in a single model.

Under the hood, this feature spans 30 source files covering:

- Unified agent configuration with validation and defaults
- Environment variable compatibility that checks ATTUNE_ then EMPATHY_ prefixes
- Configuration loading, saving, and global state management

## What connects to it

This feature relates to: config, settings.

Other parts of the codebase interact with configuration through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `ModelTier` | Defines cost optimization levels for different model usage scenarios. | `src/attune/config/agent_config.py` |
| `Provider` | Specifies which LLM provider to use for agent operations. | `src/attune/config/agent_config.py` |
| `WorkflowMode` | Controls how agent workflows execute (sequential, parallel, etc.). | `src/attune/config/agent_config.py` |
| `AgentOperationError` | Provides detailed error context when agent operations fail. | `src/attune/config/agent_config.py` |
| `UnifiedAgentConfig` | Contains all configuration options for agents in a single model. | `src/attune/config/agent_config.py` |
