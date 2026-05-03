---
name: project-structure
source: .claude/CLAUDE.md
summary: This template documents the directory structure and key modules of the `attune-ai`
  package, explaining the purpose and responsibilities of each component from release
  agents and workflows to orchestration, plugins, and telemetry.
tags:
- architecture
type: note
---

# Project Structure Overview

## Context

This reference describes the directory layout of the `attune-ai` package.

## Structure

```text
src/attune/
├── agents/            # Release agents, state persistence, and recovery
│   ├── release/       # ReleaseAgent and ReleasePrepTeam
│   └── state/         # AgentStateStore and AgentRecoveryManager
├── workflows/         # AI-powered workflows (all SDK-native)
├── models/            # Authentication strategies and LLM providers
├── meta_workflows/    # Intent detection and natural language routing
├── orchestration/     # Dynamic teams, workflow composition, and agent models
├── plugins/           # BasePlugin and the register_mcp_tools() hook
├── telemetry/         # FeedbackLoop and UsageTracker (MemoryBackend protocol)
└── cli_router.py      # Natural language command routing

attune_redis/          # attune-redis plugin — install via: pip install attune-redis
```

## Key Modules

| Path | Responsibility |
|---|---|
| `agents/release/` | Manages the full release agent lifecycle |
| `agents/state/` | Handles agent state persistence and crash recovery |
| `workflows/` | Houses all SDK-native, AI-powered workflow definitions |
| `models/` | Configures authentication and LLM provider integrations |
| `meta_workflows/` | Routes natural language input to the appropriate workflow |
| `orchestration/` | Composes dynamic teams and coordinates multi-agent execution |
| `plugins/` | Provides the extension point for registering MCP tools |
| `telemetry/` | Tracks usage and feedback via a pluggable memory backend |
| `cli_router.py` | Entry point for natural language CLI command dispatch |

## Related Topics

_No related topics yet._
