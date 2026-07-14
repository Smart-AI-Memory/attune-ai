---
type: faq
name: orchestration-faq
feature: orchestration
depth: faq
generated_at: 2026-07-14T15:58:56.374113+00:00
source_hash: 3da859c638c01505e80876fc298c0d02f94889242bbb1c93df05af5291945567
status: generated
---

# Orchestration FAQ

## What does orchestration give me beyond a single workflow?

The composable parts — reusable agent templates and a library
of execution strategies — plus `AgentTeam` to fan several
workflow-backed agents out in parallel behind quality gates.

## How do I run a team of agents?

`attune.agents.team.AgentTeam(agents, gates)` with
`WorkflowAgent`s and `GateSpec`s, then `await team.run(target)`.

## How do I see the available agent templates?

`get_all_templates()` (and `get_template(id)` for one); filter
with `get_templates_by_capability` / `get_templates_by_tier`.

## Is orchestration sync or async?

Building a team and listing templates are synchronous;
`AgentTeam.run` and `ExecutionStrategy.execute` are async.
