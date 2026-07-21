---
description: Choose your learning path for Attune AI. Quick Start, Tutorial, or Deep Dive approaches based on your experience level.
---

# Choose Your Path

You've installed the framework and run your first workflow. Now choose the approach that fits your needs.

---

## Four Ways to Use Attune AI

| Path | Best For | Complexity |
|------|----------|------------|
| [CLI Power User](#path-1-cli-power-user) | Quick tasks, automation, CI/CD | Simple |
| [MCP Integration](#path-2-mcp-integration) | Claude Desktop, conversational workflow building | Simple |
| [Workflow Developer](#path-3-workflow-developer) | Custom automations, Python integration | Moderate |
| [Multi-Agent Teams](#path-4-multi-agent-teams) | Fan out several workflows with quality gates | Advanced |

---

## Path 1: CLI Power User

**Best for:** Quick tasks, shell scripts, CI/CD pipelines

Use the `empathy` CLI to run pre-built workflows without writing Python.

### Key Commands

```bash
# Run workflows
attune workflow run security-audit --path ./src
attune workflow run bug-predict --path ./src
attune workflow run release-prep --path .

# Track costs
attune telemetry show
attune telemetry savings --days 30
```

### Next Steps

- [CLI Reference](../reference/cli-reference.md) - Complete command reference
- Run `attune --help` for a quick command reference

---

## Path 2: MCP Integration

**Best for:** Claude Desktop users, conversational workflow building

Connect to Claude Desktop or any MCP-compatible client for guided workflow creation.

### Quick Setup

Add to Claude Desktop config:

```json
{
    "mcpServers": {
        "attune-ai": {
            "command": "python",
            "args": ["-m", "attune.mcp.server"],
            "env": {"ANTHROPIC_API_KEY": "your-key"}
        }
    }
}
```

Then ask Claude to help you build workflows conversationally.

### Next Steps

- [MCP Integration Guide](mcp-integration.md) - Full setup instructions
- [Tutorials](../tutorials/index.md) - Guided workflow building

---

## Path 3: Workflow Developer

**Best for:** Custom automations, integrating AI into Python apps

Use the Python API to run and build workflows.

### Using Built-in Workflows

```python
from attune.workflows import SecurityAuditWorkflow
import asyncio

async def audit():
    workflow = SecurityAuditWorkflow()
    result = await workflow.execute(target_path="./src")
    print(f"Found {len(result.findings)} issues")

asyncio.run(audit())
```

### Next Steps

- Python API Reference - Full API documentation
- [Practical Patterns](../how-to/practical-patterns.md) - Ready-to-use patterns

---

## Path 4: Multi-Agent Teams

**Best for:** Running several workflows in parallel behind quality gates

Fan out a fixed set of workflow-backed agents over a target, then gate
on their real 0-100 scores with `AgentTeam`.

```python
import asyncio
from attune.agents.team import AgentTeam, GateSpec, WorkflowAgent
from attune.workflows.code_review import CodeReviewWorkflow
from attune.workflows.security_audit import SecurityAuditWorkflow

team = AgentTeam(
    agents=[
        WorkflowAgent("code-review", CodeReviewWorkflow, files=["src/"]),
        WorkflowAgent("security-audit", SecurityAuditWorkflow, files=["src/"]),
    ],
    gates=[
        GateSpec("Code Quality", "code-review", 80.0),
        GateSpec("Security", "security-audit", 80.0),
    ],
)
report = asyncio.run(team.run(["src/"]))
print(report.passed, report.blockers)
```

### Next Steps

- [Multi-Agent Teams example](../tutorials/examples/multi-agent-team-coordination.md)
- Practical Patterns

---

## Still Not Sure?

| If you want to... | Start with... |
|-------------------|---------------|
| Run quick tasks from terminal | CLI |
| Use Claude Desktop | MCP Integration |
| Build custom Python apps | Workflow Developer |
| Run several workflows behind quality gates | Multi-Agent Teams |

**Most users start with CLI or MCP.** Move to Workflow Developer when you need custom logic, and Multi-Agent Teams when you want to fan several workflows out behind gates.
