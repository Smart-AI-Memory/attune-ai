---
type: note
name: project-structure
tags: [architecture]
source: .claude/CLAUDE.md
---

# Note: Project structure overview

## Context

Directory layout of the attune-ai package.

## Content

```text
src/attune/
├── agents/            # Release agents, state persistence, recovery
│   ├── release/       # ReleaseAgent, ReleasePrepTeam
│   └── state/         # AgentStateStore, AgentRecoveryManager
├── workflows/         # AI-powered workflows (all SDK-native)
├── models/            # Authentication strategy and LLM providers
├── meta_workflows/    # Intent detection and natural language routing
├── orchestration/     # Dynamic teams, workflow composition, agent models
├── plugins/           # BasePlugin + register_mcp_tools() hook
├── telemetry/         # FeedbackLoop, UsageTracker (MemoryBackend protocol)
└── cli_router.py      # Natural language command routing

attune_redis/          # attune-redis plugin (pip install attune-redis)
```

## Related Topics

_No related topics yet._
