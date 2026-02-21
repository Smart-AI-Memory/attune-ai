---
name: sdk-agent
description: "Anthropic Agent SDK integration"
type: subagent
team: sdk
coordination: sequential
tier_strategy: escalation
---

# SDK Agent

Wraps the Anthropic Agent SDK with attune's tier escalation,
heartbeats, and persistent state patterns.

## Features

- **Tier Escalation:** Automatic model tier progression
- **Heartbeats:** Periodic health checks during execution
- **State Persistence:** Checkpoint and resume support
- **Quality Gates:** Output quality scoring and feedback

## Installation

```bash
pip install attune-ai[agent-sdk]
```

## Usage

```text
/agent run sdk
```
