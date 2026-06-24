---
type: comparison
name: orchestration-comparison
feature: orchestration
depth: comparison
generated_at: 2026-06-24T04:42:36.420317+00:00
source_hash: 8eeb348f730d4eaa712d0cf9b78905ce878837e5c821fc161778c91d1d163103
status: generated
---

# Dynamic agent teams, workflow composition, and meta-orchestration of multi-agent pipelines

## Comparison

| | a workflow | orchestration | the agents feature |
|--|-----------|---------------|--------------------|
| Scope | one analysis | coordinating several agents into a pipeline | the agent factory that builds agents |
| Entry | `attune workflow run` | `MetaOrchestrator` / `DynamicTeamBuilder` | the agent factory |
| Output | a result | a `StrategyResult` over a team | an agent |

Orchestration consumes agent templates and runs them; it does not
replace the per-workflow analyses — it composes them.
