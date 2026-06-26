---
description: "Example: Multi-Agent Team Coordination — run a fan-out team of workflow agents with a quality gate."
---

# Example: Multi-Agent Team Coordination

**Difficulty**: Advanced
**Time**: 15 minutes
**Domain**: Software Development

---

## Overview

This example shows how to run several analysis workflows in parallel
as a coordinated team, then enforce a quality gate on the results.

The `AgentTeam` API fans out across multiple `WorkflowAgent`s,
runs them concurrently against the same target, and evaluates
`GateSpec` thresholds against each agent's score.

**Use Case**: Run a code-review agent and a security-audit agent
together over the same source tree, then fail the run if code
quality falls below a threshold.

**What you'll learn**:

- Defining a team of workflow agents
- Running agents in parallel (fan-out)
- Enforcing a quality gate on agent scores

---

## Installation

```bash
pip install attune-ai
```

---

## Build and Run a Team

`AgentTeam` is fan-out plus gate: every agent runs concurrently
against the target, and each `GateSpec` checks one agent's score
against a threshold.

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
    gates=[GateSpec("Code Quality", "code-review", 80.0)],
)

report = asyncio.run(team.run(["src/"]))
print(report)
```

The call returns a `TeamReport` summarizing each agent's result
and whether every gate passed.

---

## Sharing Patterns Across Runs

Teams can also draw on a shared pattern library so that a pattern
discovered in one run is available to later runs.

```python
from attune import PatternLibrary, Pattern

library = PatternLibrary()
pattern = Pattern(
    id="db-index-opt",
    agent_id="backend",
    pattern_type="optimization",
    name="database_index_optimization",
    description="Add a database index on frequently queried fields",
    confidence=0.95,
)
library.contribute_pattern(agent_id="backend", pattern=pattern)

stats = library.get_library_stats()
print(f"Patterns available: {stats['total_patterns']}")
```

---

## Next Steps

**Extend the team**:

1. **Add more agents**: include additional analysis workflows
2. **Add more gates**: enforce thresholds on every agent
3. **Escalate agents**: set `escalate=True` on a `WorkflowAgent`
   to run it at a higher model tier

---

## Troubleshooting

**Gate fails unexpectedly**

- Lower the `GateSpec` threshold, or pass `critical=False` to make
  the gate advisory rather than blocking.

**An agent reports no findings**

- Verify the `files` list points at real paths relative to the
  working directory.

---

**Questions?** See the
[Multi-Agent Coordination guide](../how-to/multi-agent-coordination.md).
