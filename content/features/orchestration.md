---
feature: orchestration
summary: Reusable agent templates, a library of execution strategies, and parallel agent teams with quality gates
tags: [orchestration, teams]
source_globs:
  - src/attune/orchestration/**
  - src/attune/agents/team.py
nav:
  help: orchestration
  mkdocs:
    how-to: how-to/orchestration
    architecture: architecture/orchestration
    reference: reference/orchestration
---

## Overview

`attune.orchestration` supplies the **composable building blocks** for
multi-agent work: a registry of reusable **agent templates** and a
library of **execution strategies**. It sits above the individual
workflows — where a workflow is one analysis, these parts let you
describe and combine *several* agents.

To actually run a team, use `attune.agents.team.AgentTeam`: it fans a
fixed set of workflow-backed agents out in parallel, scores each, and
gates the result. There is no task-analysis planner that picks agents
for you — you choose the agents and the gates.

## Concepts

### Agent templates — the registry

The registry supplies reusable `AgentTemplate`s (each has an `id`,
`role`, `capabilities`, `tools`, `tier_preference`, `quality_gates`, and
`resource_requirements`). Query it with `get_all_templates()`,
`get_template(template_id)`, `get_templates_by_capability(...)`,
`get_templates_by_tier(...)`, and `get_registry()`; extend it with
`register_custom_template(...)` / `unregister_template(...)`.
`AgentCapability` and `ResourceRequirements` model a template's
capabilities and resource needs.

### Execution strategies — the composition library

An `ExecutionStrategy` runs a list of agents:
`execute(agents, context)` is **async** and returns a `StrategyResult`
(`success`, `outputs`, `aggregated_output`, `total_duration`,
`errors`). `get_strategy(name)` returns a strategy by name. Nine names
construct with **no arguments** — `sequential`, `parallel`, `debate`,
`teaching`, `refinement`, `adaptive`, `tool_enhanced`,
`prompt_cached_sequential`, `delegation_chain`. The registry also holds
`conditional`, `multi_conditional`, `nested`, and `nested_sequential`,
but those require constructor args, so fetching them bare via
`get_strategy` raises `TypeError` — construct them directly. The classes
exported directly from `attune.orchestration` are the base
`ExecutionStrategy` plus `ToolEnhancedStrategy`,
`PromptCachedSequentialStrategy`, and `DelegationChainStrategy`.

### Agent teams — fan-out + gate

`attune.agents.team.AgentTeam(agents, gates)` is the runnable team
primitive. Each `WorkflowAgent(key, workflow_cls, *, files=...)` wraps a
registered workflow and reports a real 0-100 score; each
`GateSpec(name, agent_key, threshold, critical=True)` thresholds one
agent's score. `await team.run(target)` runs the agents in parallel over
a path (or list of paths) and returns a `TeamReport` (`passed`, `gates`,
`results`, `blockers`, `warnings`, `cost`). It is **fan-out + gate
only** — no sequential/two-phase/DAG topology and no auto-composition.

## Quickstart

Inspect the agent templates and grab a strategy:

```python
from attune.orchestration import get_all_templates, get_strategy

templates = get_all_templates()
print(len(templates), "templates; e.g.", templates[0].id)

strategy = get_strategy("sequential")
print(type(strategy).__name__)
```

## Tasks

### Run a multi-agent quality gate

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
print(report.passed, report.blockers, report.warnings)
```

**Verify:** `team.run(target)` is **async** and returns a `TeamReport`
with `passed`, `blockers`, `warnings`, `results`, and `cost`.

### Find agent templates by capability or tier

```python
from attune.orchestration import (
    get_all_templates,
    get_template,
    get_templates_by_tier,
)

all_templates = get_all_templates()
one = get_template(all_templates[0].id)
print(one.role, [str(c) for c in one.capabilities])
```

**Verify:** `get_all_templates()` returns the registry's templates;
`get_template(template_id)` returns one (or `None`);
`get_templates_by_capability` / `get_templates_by_tier` filter the set.

### Pick an execution strategy

```python
from attune.orchestration import get_strategy

strategy = get_strategy("parallel")
print(type(strategy).__name__)
```

**Verify:** `get_strategy(name)` resolves the nine no-arg strategy names
above to a strategy. Running it — `await strategy.execute(agents,
context)` — is **async** and returns a `StrategyResult`.

## Reference

### Agent teams

| Symbol | Purpose |
|--------|---------|
| `AgentTeam(agents, gates)` | Fan-out + gate runner; `await run(target)` → `TeamReport`. |
| `WorkflowAgent(key, workflow_cls, *, files=...)` | Wrap a workflow as a scored agent. |
| `GateSpec(name, agent_key, threshold, critical=True)` | Threshold one agent's score; `critical=False` → warning, not blocker. |
| `TeamReport` | `passed`, `gates`, `results`, `blockers`, `warnings`, `cost`. |
| `AgentResult` | Per-agent `key`, `score`, `cost`, `success`, `details`. |

### Agent templates

| Symbol | Purpose |
|--------|---------|
| `get_all_templates()` / `get_template(id)` | Registry access. |
| `get_templates_by_capability(...)` / `get_templates_by_tier(...)` | Filter templates. |
| `register_custom_template(...)` / `unregister_template(...)` / `get_registry()` | Extend/inspect the registry. |
| `AgentTemplate` | `id`, `role`, `capabilities`, `tools`, `tier_preference`, `quality_gates`, `resource_requirements`. |
| `AgentCapability` / `ResourceRequirements` | Capability + resource models. |

### Execution strategies

| Symbol | Purpose |
|--------|---------|
| `ExecutionStrategy` | Base; `execute(agents, context)` is **async** → `StrategyResult`. |
| `get_strategy(name)` | Resolve a no-arg strategy (9 names). `conditional`/`multi_conditional`/`nested`/`nested_sequential` are registered too but need constructor args. |
| `ToolEnhancedStrategy` / `PromptCachedSequentialStrategy` / `DelegationChainStrategy` | Exported concrete strategies. |

## Comparison

| | a workflow | orchestration | the agents feature |
|--|-----------|---------------|--------------------|
| Scope | one analysis | the parts that combine agents | the agent factory that builds agents |
| Entry | `attune workflow run` | `AgentTeam` / `get_strategy` / templates | the agent factory |
| Output | a result | a `TeamReport` or `StrategyResult` | an agent |

Orchestration consumes agent templates and workflows and runs them; it
does not replace the per-workflow analyses — it composes them.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'run' was never awaited` | `AgentTeam.run` / `ExecutionStrategy.execute` called without `await` | both are async — `await` them | high |
| `get_strategy(name)` raises | unknown name (`ValueError`), or an arg-taking name like `conditional`/`nested` (`TypeError`) | use one of the nine no-arg names; construct arg-taking strategies directly | medium |
| `get_template(id)` returns `None` | no template with that id | list ids via `get_all_templates()` | low |
| A gate blocks but the agent never ran | a `GateSpec.agent_key` does not match any `WorkflowAgent.key` | the agent has no score so the gate fails closed — align the keys | medium |

### Risk areas

- **`run` and `execute` are async.** `AgentTeam.run` and
  `ExecutionStrategy.execute` must be awaited.
- **`get_strategy` resolves the nine no-arg strategies.** The registry
  also holds `conditional`/`multi_conditional`/`nested`/
  `nested_sequential`, which require constructor args (fetching them bare
  raises `TypeError`).
- **Gates fail closed.** A `GateSpec` whose agent errored or produced no
  score fails the gate rather than passing silently.

### Diagnosis order

1. `get_all_templates()` — what agents/templates are available?
2. Are `GateSpec.agent_key`s aligned with `WorkflowAgent.key`s?
3. `get_strategy(name)` — is the strategy name valid?
4. Async-not-awaited? `run` / `execute` must be awaited.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** Author-curated seeds, merged
> by the FAQ Generator with live signals. Not projected verbatim.

- **Q:** What does orchestration give me beyond a single workflow?
  **A:** The composable parts — reusable agent templates and a library
  of execution strategies — plus `AgentTeam` to fan several
  workflow-backed agents out in parallel behind quality gates.
- **Q:** How do I run a team of agents?
  **A:** `attune.agents.team.AgentTeam(agents, gates)` with
  `WorkflowAgent`s and `GateSpec`s, then `await team.run(target)`.
- **Q:** How do I see the available agent templates?
  **A:** `get_all_templates()` (and `get_template(id)` for one); filter
  with `get_templates_by_capability` / `get_templates_by_tier`.
- **Q:** Is orchestration sync or async?
  **A:** Building a team and listing templates are synchronous;
  `AgentTeam.run` and `ExecutionStrategy.execute` are async.

## Notes & tips

- **Await the run.** `AgentTeam.run` and `execute` are async.
- **Start from templates.** `get_all_templates()` is the cheapest way to
  see what a team can be built from.
- **`get_strategy` takes a registry name**, not a class.
- **`AgentTeam` is fan-out + gate**, not a planner — you pick the agents
  and the gates.

## Design & extension

### Design decisions

- **Building blocks over a planner.** `attune.orchestration` provides
  reusable templates and a strategy library; `AgentTeam` runs an
  explicit team. There is no task-analysis layer choosing agents for you.
- **Templates over ad-hoc agents.** Reusable `AgentTemplate`s matched by
  capability/tier keep team assembly declarative.
- **Gates fail closed.** A team only passes when every critical gate's
  agent produced a passing score — never on a missing or errored score.

### Extension points

- **Custom template:** `register_custom_template(...)`.
- **Custom team:** assemble `WorkflowAgent`s + `GateSpec`s into an
  `AgentTeam`.
- **Custom strategy:** subclass `ExecutionStrategy` and implement the
  async `execute(agents, context)`.
