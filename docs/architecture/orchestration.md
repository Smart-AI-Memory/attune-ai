# Orchestration

## Overview

`attune.orchestration` supplies the building blocks for **multi-agent
pipelines**: a registry of reusable agent templates and a set of
execution strategies that run agents and return a result. It sits above
the individual workflows — where a workflow is one analysis,
orchestration coordinates *several* agents into one coordinated run.

An orchestrated task has two layers:

1. **Team assembly** — `AgentTemplate`s are matched by capability/tier
   from the registry.
2. **Execution** — an `ExecutionStrategy` runs the agents and returns a
   `StrategyResult`.

For a ready-made fan-out gate that runs workflows as agents and applies
pass/fail thresholds, `attune.agents.team.AgentTeam` wraps this into a
single call.

## Concepts

### Team assembly — agent templates

The agent registry supplies reusable `AgentTemplate`s (each has an `id`,
`role`, `capabilities`, `tools`, `tier_preference`, `quality_gates`, and
`resource_requirements`). Query it with `get_all_templates()`,
`get_template(template_id)`, `get_templates_by_capability(...)`,
`get_templates_by_tier(...)`, and `get_registry()`; extend it with
`register_custom_template(...)` / `unregister_template(...)`.
`AgentCapability` and `ResourceRequirements` model a template's
capabilities and resource needs.

### Execution — strategies

An `ExecutionStrategy` runs the assembled agents:
`execute(agents, context)` is **async** and returns a `StrategyResult`.
`get_strategy(name)` returns a strategy by name. Nine names construct
with **no arguments** — `sequential`, `parallel`, `debate`, `teaching`,
`refinement`, `adaptive`, `tool_enhanced`, `prompt_cached_sequential`,
`delegation_chain`. The registry also holds `conditional`,
`multi_conditional`, `nested`, and `nested_sequential`, but those require
constructor args, so fetching them bare via `get_strategy` raises
`TypeError` — construct them directly. The classes exported directly from
`attune.orchestration` are the base `ExecutionStrategy` plus
`ToolEnhancedStrategy`, `PromptCachedSequentialStrategy`, and
`DelegationChainStrategy`.

### Fan-out gate — `AgentTeam`

`AgentTeam` runs a fixed set of workflow-backed agents in parallel and
applies pass/fail gates to their scores. Each agent is a `WorkflowAgent`
(a workflow class plus the files it inspects); each gate is a `GateSpec`
(a name, the agent key it reads, and a score threshold). `team.run(...)`
is **async** and returns a `TeamReport` carrying `passed`, the per-agent
`results`, and aggregated `blockers`, `warnings`, and `cost`.

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
print(report.passed, report.blockers, report.warnings, report.cost)
```

`AgentTeam` is fan-out plus gating only — there is no sequential,
two-phase, or DAG topology, and no pluggable strategy. For richer
coordination, drive the `ExecutionStrategy` registry directly.

## Design & extension

### Design decisions

- **Two separable layers.** Assembly (templates) and execution
  (`ExecutionStrategy`) are decoupled, so a strategy can be swapped
  without touching the agents.
- **Templates over ad-hoc agents.** Reusable `AgentTemplate`s matched by
  capability/tier keep team assembly declarative.
- **Async execution.** The actual multi-agent run is async, whether
  through a strategy or through `AgentTeam.run(...)`.

### Extension points

- **Custom agent:** `register_custom_template(...)`.
- **Gated workflow team:** compose `WorkflowAgent`s and `GateSpec`s into
  an `AgentTeam`.

<!-- attune-generated: source_hash=8eeb348f730d4eaa712d0cf9b78905ce878837e5c821fc161778c91d1d163103 feature=orchestration kind=architecture generated_at=2026-06-24 -->
