---
name: orchestration
source: content/features/orchestration.md
tags:
- orchestration
- teams
type: concept
---

# Reusable agent templates, a library of execution strategies, and parallel agent teams with quality gates

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
