---
name: agent
description: Create and manage custom AI agents and teams
---
# agent

Create and manage custom AI agents and teams using
the Attune Agent SDK.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `create` | Create a new agent |
| `create-team` | Create a multi-agent team |
| `run` | Run an existing agent |
| `list` | List available agents |
| `release-prep` | Run release prep agent team |

## Usage

```bash
/agent                  # Ask what to do
/agent create           # Create an agent
/agent create-team      # Create a team
/agent run              # Run an agent
/agent list             # List agents
/agent release-prep     # Run release prep team
```

## Behavior

### create

Use `AskUserQuestion` to understand:

- What should the agent do?
- What tier? (cheap, capable, premium)
- What tools does it need?

Then guide the user through agent definition using
the SDK:

```python
from attune.agents.sdk import SDKAgent

agent = SDKAgent(
    agent_id="my-agent",
    role="analyst",
    tier="capable",
)
```

### create-team

Use `AskUserQuestion` to understand:

- What's the team's goal?
- How many agents?
- What roles?

Then guide through team creation:

```python
from attune.agents.sdk import SDKAgentTeam

team = SDKAgentTeam(
    team_id="my-team",
    agents=[agent1, agent2],
)
```

### run

Use `AskUserQuestion`:

- Which agent or team to run?
- What input?

Then execute the agent.

### list

Show available agents and teams from the registry.

### release-prep

Run the release preparation agent team:

```bash
uv run attune workflow run release-prep
```
