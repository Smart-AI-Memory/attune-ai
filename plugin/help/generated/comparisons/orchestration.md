---
name: orchestration
source: content/features/orchestration.md
tags:
- orchestration
- teams
type: comparison
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
