---
feature: orchestration
summary: Dynamic agent teams, workflow composition, and meta-orchestration of multi-agent pipelines
tags: [orchestration, teams]
source_globs:
  - src/attune/orchestration/**
nav:
  help: orchestration
  mkdocs:
    how-to: how-to/orchestration
    architecture: architecture/orchestration
    reference: reference/orchestration
---

## Overview

`attune.orchestration` assembles and runs **multi-agent pipelines**: it
analyzes a task, picks a composition pattern, builds a team of agents,
and executes them under a chosen strategy. It sits above the individual
workflows — where a workflow is one analysis, orchestration coordinates
*several* agents into one coordinated run.

An orchestrated task moves through three layers:

1. **Meta-orchestration** — `MetaOrchestrator` analyzes the task
   (complexity, domain, requirements) and chooses a `CompositionPattern`.
2. **Team assembly** — `AgentTemplate`s are matched by capability/tier
   from the registry, or a `DynamicTeamBuilder` builds a team at runtime.
3. **Execution** — an `ExecutionStrategy` runs the agents and returns a
   `StrategyResult`.

## Concepts

### Meta-orchestration — `MetaOrchestrator`

`MetaOrchestrator` is the planning layer. Its methods are synchronous:
`analyze_task(...)` returns a `TaskRequirements` (carrying a
`TaskComplexity` — `SIMPLE` / `MODERATE` / `COMPLEX` — and a `TaskDomain`
— `TESTING` / `SECURITY` / `CODE_QUALITY` / `DOCUMENTATION` /
`PERFORMANCE` / `ARCHITECTURE` / `REFACTORING` / `GENERAL`);
`create_execution_plan(...)` returns an `ExecutionPlan`;
`compose_team(...)` and `analyze_and_compose(...)` go from a task
description to a composed team.

`CompositionPattern` enumerates the strategies the planner can pick:
`SEQUENTIAL`, `PARALLEL`, `DEBATE`, `TEACHING`, `REFINEMENT`,
`ADAPTIVE`, `CONDITIONAL`, `TOOL_ENHANCED`, `PROMPT_CACHED_SEQUENTIAL`,
`DELEGATION_CHAIN`.

### Team assembly — agent templates and dynamic teams

The agent registry supplies reusable `AgentTemplate`s (each has an `id`,
`role`, `capabilities`, `tools`, `tier_preference`, `quality_gates`, and
`resource_requirements`). Query it with `get_all_templates()`,
`get_template(template_id)`, `get_templates_by_capability(...)`,
`get_templates_by_tier(...)`, and `get_registry()`; extend it with
`register_custom_template(...)` / `unregister_template(...)`.
`AgentCapability` and `ResourceRequirements` model a template's
capabilities and resource needs.

`DynamicTeamBuilder(state_store=None, redis_client=None)` builds a team
at runtime — `build_from_spec(...)`, `build_from_plan(...)`,
`build_from_config(...)` — producing a `DynamicTeam` /
`DynamicTeamResult` from a `TeamSpecification`. `TeamStore` persists
teams.

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

### Workflow composition

`WorkflowComposer(state_store=None)` composes workflows —
`compose(...)` and `compose_with_simplification(...)`.
`WorkflowAgentAdapter` adapts a workflow so it can run as an agent
inside a team.

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

### Analyze a task and plan its orchestration

```python
from attune.orchestration import MetaOrchestrator

orch = MetaOrchestrator()
reqs = orch.analyze_task("audit security and add tests")
print(reqs.complexity, reqs.domain)
```

**Verify:** `analyze_task(...)` is synchronous and returns a
`TaskRequirements` with a `complexity` (`TaskComplexity`) and `domain`
(`TaskDomain`). `create_execution_plan(...)` turns that into an
`ExecutionPlan`.

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

### Meta-orchestration

| Symbol | Purpose |
|--------|---------|
| `MetaOrchestrator()` | `analyze_task`, `create_execution_plan`, `compose_team`, `analyze_and_compose` (all sync). |
| `TaskRequirements` / `ExecutionPlan` | Planner inputs/outputs. |
| `TaskComplexity` | `SIMPLE` / `MODERATE` / `COMPLEX`. |
| `TaskDomain` | `TESTING` / `SECURITY` / `CODE_QUALITY` / `DOCUMENTATION` / `PERFORMANCE` / `ARCHITECTURE` / `REFACTORING` / `GENERAL`. |
| `CompositionPattern` | The 10 patterns (SEQUENTIAL … DELEGATION_CHAIN). |

### Team assembly

| Symbol | Purpose |
|--------|---------|
| `get_all_templates()` / `get_template(id)` | Registry access. |
| `get_templates_by_capability(...)` / `get_templates_by_tier(...)` | Filter templates. |
| `register_custom_template(...)` / `unregister_template(...)` / `get_registry()` | Extend/inspect the registry. |
| `AgentTemplate` | `id`, `role`, `capabilities`, `tools`, `tier_preference`, `quality_gates`, `resource_requirements`. |
| `AgentCapability` / `ResourceRequirements` | Capability + resource models. |
| `DynamicTeamBuilder(state_store=None, redis_client=None)` | `build_from_spec` / `build_from_plan` / `build_from_config`. |
| `DynamicTeam` / `DynamicTeamResult` / `TeamSpecification` / `TeamStore` | Team objects + persistence. |

### Execution & composition

| Symbol | Purpose |
|--------|---------|
| `ExecutionStrategy` | Base; `execute(agents, context)` is **async** → `StrategyResult`. |
| `get_strategy(name)` | Resolve a no-arg strategy (9 names). `conditional`/`multi_conditional`/`nested`/`nested_sequential` are registered too but need constructor args. |
| `ToolEnhancedStrategy` / `PromptCachedSequentialStrategy` / `DelegationChainStrategy` | Exported concrete strategies. |
| `WorkflowComposer(state_store=None)` | `compose` / `compose_with_simplification`. |
| `WorkflowAgentAdapter` | Run a workflow as a team agent. |

## Comparison

| | a workflow | orchestration | the agents feature |
|--|-----------|---------------|--------------------|
| Scope | one analysis | coordinating several agents into a pipeline | the agent factory that builds agents |
| Entry | `attune workflow run` | `MetaOrchestrator` / `DynamicTeamBuilder` | the agent factory |
| Output | a result | a `StrategyResult` over a team | an agent |

Orchestration consumes agent templates and runs them; it does not
replace the per-workflow analyses — it composes them.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'execute' was never awaited` | `ExecutionStrategy.execute` called without `await` | it is async — `await` it | high |
| `get_strategy(name)` raises | unknown name (`ValueError`), or an arg-taking name like `conditional`/`nested` (`TypeError`) | use one of the nine no-arg names; construct arg-taking strategies directly | medium |
| `get_template(id)` returns `None` | no template with that id | list ids via `get_all_templates()` | low |
| Team build fails | a `TeamSpecification` references an unknown template/capability | check the spec against `get_all_templates()` | medium |

### Risk areas

- **Planning is sync; execution is async.** `MetaOrchestrator` methods
  and the builders are synchronous; `ExecutionStrategy.execute` is
  async.
- **`get_strategy` resolves the nine no-arg strategies.** The registry
  also holds `conditional`/`multi_conditional`/`nested`/
  `nested_sequential`, which require constructor args (fetching them bare
  raises `TypeError`).
- **Templates are matched by capability/tier.** A team is only as good
  as the templates the registry can supply.

### Diagnosis order

1. `get_all_templates()` — what agents are available?
2. `MetaOrchestrator().analyze_task(...)` — what does the planner infer?
3. `get_strategy(name)` — is the strategy name valid?
4. Async-not-awaited? `execute` must be awaited.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** Author-curated seeds, merged
> by the FAQ Generator with live signals. Not projected verbatim.

- **Q:** What does orchestration do that a single workflow doesn't?
  **A:** It coordinates *several* agents into one pipeline — analyzing
  the task, picking a `CompositionPattern`, assembling a team, and
  running it under an `ExecutionStrategy`.
- **Q:** How do I see the available agents?
  **A:** `get_all_templates()` (and `get_template(id)` for one); filter
  with `get_templates_by_capability` / `get_templates_by_tier`.
- **Q:** Which execution strategies exist?
  **A:** `get_strategy(name)` resolves nine no-arg strategies:
  `sequential`, `parallel`, `debate`, `teaching`, `refinement`,
  `adaptive`, `tool_enhanced`, `prompt_cached_sequential`,
  `delegation_chain` (the registry also holds `conditional`/`nested`
  variants that need constructor args).
- **Q:** Is orchestration sync or async?
  **A:** Planning and team assembly are synchronous;
  `ExecutionStrategy.execute(agents, context)` is async.

## Notes & tips

- **Plan sync, execute async.** `MetaOrchestrator` / builders are sync;
  `execute` is async.
- **Start from templates.** `get_all_templates()` is the cheapest way to
  see what a team can be built from.
- **`get_strategy` takes a registry name**, not a class.
- **Orchestration composes workflows; it doesn't replace them.**

## Design & extension

### Design decisions

- **Three separable layers.** Planning (`MetaOrchestrator`), assembly
  (templates + `DynamicTeamBuilder`), and execution
  (`ExecutionStrategy`) are decoupled, so a strategy can be swapped
  without touching the agents.
- **Templates over ad-hoc agents.** Reusable `AgentTemplate`s matched by
  capability/tier keep team assembly declarative.
- **Sync planning, async execution.** Planning is cheap and synchronous;
  the actual multi-agent run is async.

### Extension points

- **Custom agent:** `register_custom_template(...)`.
- **Custom team:** a `TeamSpecification` → `DynamicTeamBuilder`.
- **Run a workflow as an agent:** `WorkflowAgentAdapter`.
