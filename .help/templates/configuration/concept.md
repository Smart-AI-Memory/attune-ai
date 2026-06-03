---
feature: configuration
depth: concept
generated_at: 2026-06-03T02:40:23.627042+00:00
source_hash: c8fb692ea17a00968fafe6e570ae09d569d1880728837d9636497e05d1a9d9ed
status: generated
---

# Configuration

## How it works

Project configuration and settings management.

The main building blocks are:

- **`ModelTier`** — Model tier for cost optimization.
- **`Provider`** — LLM provider options.
- **`WorkflowMode`** — Workflow execution modes.
- **`AgentOperationError`** — Error during agent operation with context.
- **`UnifiedAgentConfig`** — Unified configuration model for all agents.

Under the hood, this feature spans 15 source
files covering:

- Unified Agent Configuration
- Environment variable compatibility layer.
- Configuration loader for Attune AI.

## What connects to it

This feature relates to: config, settings.

Other parts of the codebase interact with
configuration through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `ModelTier` | Model tier for cost optimization. | `src/attune/config/agent_config.py` |
| `Provider` | LLM provider options. | `src/attune/config/agent_config.py` |
| `WorkflowMode` | Workflow execution modes. | `src/attune/config/agent_config.py` |
| `AgentOperationError` | Error during agent operation with context. | `src/attune/config/agent_config.py` |
| `UnifiedAgentConfig` | Unified configuration model for all agents. | `src/attune/config/agent_config.py` |
