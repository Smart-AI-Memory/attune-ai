---
name: state-manager
description: "Persistent agent state and recovery"
type: subagent
team: state
coordination: internal
---

# State Manager Agent

Provides storage, retrieval, and recovery of agent execution
history and checkpoint data.

## Features

- **State Store:** Persistent agent state records
- **Execution History:** Track agent runs and outcomes
- **Recovery:** Automatic checkpoint and resume on failure
- **Audit Trail:** Full execution record for debugging

## Components

| Component | Purpose |
| --------- | ------- |
| AgentStateStore | Persistent state storage |
| AgentStateRecord | State data model |
| AgentExecutionRecord | Execution history |
| AgentRecoveryManager | Failure recovery |
