# Orchestration

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

<!-- attune-generated: source_hash=8eeb348f730d4eaa712d0cf9b78905ce878837e5c821fc161778c91d1d163103 feature=orchestration kind=architecture generated_at=2026-06-24 -->
