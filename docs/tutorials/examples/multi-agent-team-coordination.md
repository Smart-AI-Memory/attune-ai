---
description: "Multi-Agent Team Coordination: run a team of
  workflow-backed agents in parallel, score each one, and gate
  the result with Attune's AgentTeam API."
---

# Multi-Agent Team Coordination

**Difficulty**: Advanced
**Time**: 20 minutes
**Prerequisites**: `attune-ai` installed,
`ANTHROPIC_API_KEY` set (or subscription auth configured)

---

## Overview

This tutorial shows how to coordinate multiple AI agents with
`AgentTeam`. The model is **fan-out + gate**:

- Each agent wraps a real Attune workflow (code review,
  security audit, etc.) and runs over the same target.
- Every agent runs **in parallel** and produces a numeric
  **score** plus details.
- A list of **gates** turns those scores into a pass/fail
  verdict — critical gates become *blockers*, advisory gates
  become *warnings*.

`AgentTeam` is intentionally simple: it does one thing well,
fan-out with gating. There is no sequential pipeline, no DAG,
and no two-phase topology — if you need those, compose teams
yourself in Python. (An earlier auto-composing team engine
offered those topologies; it was removed. `AgentTeam` is the
supported path.)

The three building blocks:

- **`WorkflowAgent`** — binds an agent key to a workflow class
  and the files it should analyze.
- **`GateSpec`** — a named threshold against one agent's score;
  `critical=True` blocks, `critical=False` warns.
- **`AgentTeam`** — holds the agents and gates, and runs them
  with `team.run(target)`.

---

## Installation

```bash
pip install attune-ai
```

`AgentTeam` runs Attune workflows, which call an LLM. Set
`ANTHROPIC_API_KEY` (or configure subscription auth) so the
workflows can execute. Redis is **not** required.

---

## Part 1: Your First Team

Start with two agents — one code-review agent and one
security agent — both scanning `src/`. A gate on each turns
their scores into a verdict.

```python
import asyncio

from attune.agents.team import AgentTeam, GateSpec, WorkflowAgent
from attune.workflows.code_review import CodeReviewWorkflow
from attune.workflows.security_audit import SecurityAuditWorkflow

team = AgentTeam(
    agents=[
        WorkflowAgent("code-review", CodeReviewWorkflow, files=["src/"]),
        WorkflowAgent(
            "security-audit", SecurityAuditWorkflow, files=["src/"]
        ),
    ],
    gates=[
        GateSpec("Code Quality", "code-review", 80.0),
        GateSpec("Security", "security-audit", 80.0),
    ],
)

report = asyncio.run(team.run(["src/"]))

print("Passed:", report.passed)
print("Blockers:", report.blockers)
print("Warnings:", report.warnings)
print(f"Cost: ${report.cost:.4f}")
```

Both agents run **concurrently** over `src/`. Each gate names
the agent it scores (`agent_key`) and the `threshold` the
score must meet. If every critical gate passes, `report.passed`
is `True`.

---

## Part 2: Reading the Report

`team.run()` returns a `TeamReport`. Its fields tell the whole
story:

| Field | Meaning |
| ----- | ------- |
| `passed` | `True` if every critical gate met its threshold |
| `gates` | the gate specs that were evaluated |
| `results` | one `AgentResult` per agent |
| `blockers` | messages for failed **critical** gates |
| `warnings` | messages for failed **advisory** gates |
| `cost` | total LLM cost across all agents |

Each `AgentResult` carries the per-agent outcome:

```python
import asyncio

from attune.agents.team import AgentTeam, GateSpec, WorkflowAgent
from attune.workflows.code_review import CodeReviewWorkflow

team = AgentTeam(
    agents=[
        WorkflowAgent("code-review", CodeReviewWorkflow, files=["src/"]),
    ],
    gates=[
        GateSpec("Code Quality", "code-review", 80.0),
    ],
)

report = asyncio.run(team.run(["src/"]))

for result in report.results:
    print(
        f"[{result.key}] score={result.score:.1f} "
        f"success={result.success} cost=${result.cost:.4f}"
    )
    # result.details holds the workflow's raw output dict
```

The fields on an `AgentResult` are `key`, `score`, `cost`,
`success`, and `details` (the workflow's raw output).

---

## Part 3: Critical vs Advisory Gates

A gate is **critical** by default (`critical=True`): if its
agent's score is below the threshold, the team fails and a
message lands in `report.blockers`. Set `critical=False` to
make a gate **advisory** — a miss becomes a `warning` instead
of a blocker, so the team can still pass.

```python
import asyncio

from attune.agents.team import AgentTeam, GateSpec, WorkflowAgent
from attune.workflows.code_review import CodeReviewWorkflow
from attune.workflows.security_audit import SecurityAuditWorkflow

team = AgentTeam(
    agents=[
        WorkflowAgent("security", SecurityAuditWorkflow, files=["src/"]),
        WorkflowAgent("quality", CodeReviewWorkflow, files=["src/"]),
    ],
    gates=[
        # Security must pass — a miss blocks the team.
        GateSpec("Security", "security", 80.0, critical=True),
        # Quality is advisory — a miss only warns.
        GateSpec("Quality", "quality", 90.0, critical=False),
    ],
)

report = asyncio.run(team.run(["src/"]))

if report.blockers:
    print("Blocked by:", report.blockers)
if report.warnings:
    print("Warnings:", report.warnings)
```

Use this to enforce a hard floor on the things you cannot ship
without (security), while keeping aspirational targets
(coverage, style) as non-blocking signals.

---

## Part 4: Scoping Agents to Different Files

Agents do not have to scan the same target. Give each
`WorkflowAgent` its own `files` list so specialists focus on
the areas they care about — the auth code gets a security
pass, the data layer gets a performance pass.

```python
import asyncio

from attune.agents.team import AgentTeam, GateSpec, WorkflowAgent
from attune.workflows.security_audit import SecurityAuditWorkflow
from attune.workflows.perf_audit import PerformanceAuditWorkflow

team = AgentTeam(
    agents=[
        WorkflowAgent(
            "auth-security",
            SecurityAuditWorkflow,
            files=["src/auth.py", "src/tokens.py"],
        ),
        WorkflowAgent(
            "db-perf",
            PerformanceAuditWorkflow,
            files=["src/db/queries.py"],
        ),
    ],
    gates=[
        GateSpec("Auth Security", "auth-security", 85.0),
        GateSpec("DB Performance", "db-perf", 70.0, critical=False),
    ],
)

report = asyncio.run(team.run(["src/"]))
print("Passed:", report.passed, "| Cost:", f"${report.cost:.4f}")
```

The `target` passed to `team.run()` is the overall context;
each agent's own `files` list scopes what *that* agent
analyzes.

---

## Part 5: Custom Scoring

By default an agent scores itself from its workflow output. If
you want different scoring logic, pass a `score_fn` that takes
the workflow result and returns a float (or `None` to fall
back to `default_score`). You can also set `escalate=True` to
let the underlying workflow climb to a stronger model tier.

```python
import asyncio

from attune.agents.team import AgentTeam, GateSpec, WorkflowAgent
from attune.workflows.bug_predict import BugPredictionWorkflow


def fewer_bugs_is_better(result) -> float:
    """Map predicted-bug count to a 0-100 score."""
    count = 0
    if isinstance(result, dict):
        count = len(result.get("predictions", []))
    return max(0.0, 100.0 - count * 10.0)


team = AgentTeam(
    agents=[
        WorkflowAgent(
            "bug-risk",
            BugPredictionWorkflow,
            files=["src/"],
            score_fn=fewer_bugs_is_better,
            default_score=50.0,
            escalate=True,
        ),
    ],
    gates=[
        GateSpec("Bug Risk", "bug-risk", 70.0),
    ],
)

report = asyncio.run(team.run(["src/"]))
print("Passed:", report.passed)
```

`score_fn` runs against the workflow's raw output, so its
shape depends on the workflow you wrapped. When it returns
`None`, the agent uses `default_score`.

---

## Part 6: A Release-Gate Team

Putting it together: a three-agent team that acts as a
pre-merge gate. Security is a hard blocker; quality and test
health are advisory.

```python
import asyncio

from attune.agents.team import AgentTeam, GateSpec, WorkflowAgent
from attune.workflows.code_review import CodeReviewWorkflow
from attune.workflows.security_audit import SecurityAuditWorkflow
from attune.workflows.test_audit.workflow import TestAuditWorkflow


def release_gate_team(target: str) -> AgentTeam:
    """Build a fan-out team that gates a release candidate."""
    return AgentTeam(
        agents=[
            WorkflowAgent("security", SecurityAuditWorkflow, files=[target]),
            WorkflowAgent("quality", CodeReviewWorkflow, files=[target]),
            WorkflowAgent("tests", TestAuditWorkflow, files=[target]),
        ],
        gates=[
            GateSpec("Security", "security", 85.0, critical=True),
            GateSpec("Quality", "quality", 75.0, critical=False),
            GateSpec("Test Health", "tests", 70.0, critical=False),
        ],
    )


async def main(target: str = "src/") -> None:
    team = release_gate_team(target)
    report = await team.run([target])

    verdict = "READY" if report.passed else "BLOCKED"
    print(f"Release {verdict} (cost ${report.cost:.4f})")

    for result in report.results:
        print(f"  {result.key}: {result.score:.0f}")
    for blocker in report.blockers:
        print(f"  BLOCKER: {blocker}")
    for warning in report.warnings:
        print(f"  warning: {warning}")


asyncio.run(main("src/"))
```

The three agents fan out in parallel. Only the security gate
can block; a low quality or test score surfaces as a warning
while still letting the release through.

---

## API Quick Reference

| Symbol | Import | Purpose |
| ------ | ------ | ------- |
| `AgentTeam` | `attune.agents.team` | Holds agents + gates; `await team.run(target)` |
| `WorkflowAgent` | `attune.agents.team` | Binds an agent key to a workflow class + files |
| `GateSpec` | `attune.agents.team` | Named score threshold; `critical=False` warns |
| `TeamReport` | `attune.agents.team` | Result: `passed`, `results`, `blockers`, `warnings`, `cost` |
| `AgentResult` | `attune.agents.team` | Per-agent: `key`, `score`, `cost`, `success`, `details` |

Constructor signatures:

- `WorkflowAgent(key, workflow_cls, *, files=None, score_fn=None,
  default_score=None, escalate=False)`
- `GateSpec(name, agent_key, threshold, critical=True)`
- `AgentTeam(agents, gates)`
- `await team.run(target)` — `target` is a path string or a
  list of paths.

---

## Troubleshooting

### Workflows return empty or low scores

Set `ANTHROPIC_API_KEY` in your environment, or configure
subscription auth. Without credentials the workflows cannot
call the model and produce no real findings.

### A gate references the wrong agent

`GateSpec.agent_key` must exactly match a `WorkflowAgent.key`.
A typo means the gate finds no score to evaluate.

### `team.run()` must be awaited

`run()` is a coroutine. Call it inside an `async` function or
wrap it with `asyncio.run(team.run(target))`.

---

## Next Steps

- [Agent State](https://github.com/Smart-AI-Memory/attune-ai/tree/main/src/attune/agents/state) —
  persistent state and recovery for long-running agents
- [Workflows](https://github.com/Smart-AI-Memory/attune-ai/tree/main/src/attune/workflows) —
  the full catalog of workflow classes you can wrap in a
  `WorkflowAgent`
