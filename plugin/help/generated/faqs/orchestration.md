---
name: orchestration
source: content/features/orchestration.md
tags:
- orchestration
- teams
type: faq
---

# Orchestration FAQ

## What does orchestration give me beyond a single workflow?

A workflow is one analysis. `attune.orchestration` supplies the
composable parts — reusable `AgentTemplate`s and a library of
`ExecutionStrategy` classes — and `attune.agents.team.AgentTeam` fans
several workflow-backed agents out in parallel behind quality gates.

## How do I run a team of agents?

Build an `AgentTeam(agents, gates)` from `WorkflowAgent`s and
`GateSpec`s, then `await team.run(target)`. Each `WorkflowAgent` wraps a
registered workflow and reports a real 0-100 score; each `GateSpec`
thresholds one agent's score. The run returns a `TeamReport` with
`passed`, `blockers`, `warnings`, `results`, and `cost`. It is fan-out +
gate only — there is no task-analysis planner picking agents for you.

## How do I see the available agent templates?

`get_all_templates()` returns the registry's `AgentTemplate`s (each has
an `id`, `role`, `capabilities`, `tools`, `tier_preference`); fetch one
with `get_template(template_id)`. Filter with
`get_templates_by_capability(...)` or `get_templates_by_tier(...)`, and
add your own with `register_custom_template(...)`.

## Which execution strategies can `get_strategy` return?

Nine names construct with no arguments: `sequential`, `parallel`,
`debate`, `teaching`, `refinement`, `adaptive`, `tool_enhanced`,
`prompt_cached_sequential`, `delegation_chain`. The registry also holds
`conditional`, `multi_conditional`, `nested`, and `nested_sequential`,
but those require constructor arguments — fetching them bare via
`get_strategy` raises `TypeError`, so construct them directly. An
unknown name raises `ValueError`.

## Is orchestration synchronous or asynchronous?

Building a team and listing templates are synchronous. The runs —
`AgentTeam.run(target)` and `ExecutionStrategy.execute(agents,
context)` — are **async** and must be awaited.

## Where is the source?

The templates and strategies live under `src/attune/orchestration/`; the
team runner is `attune.agents.team.AgentTeam`
(`src/attune/agents/team.py`).

**Tags:** `orchestration`, `teams`
