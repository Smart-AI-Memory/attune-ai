---
name: orchestration
source: content/features/orchestration.md
tags:
- orchestration
- teams
type: comparison
---

# Reusable agent templates, a library of execution strategies, and parallel agent teams with quality gates

## Comparison

| | a workflow | orchestration | the agents feature |
|--|-----------|---------------|--------------------|
| Scope | one analysis | the parts that combine agents | the agent factory that builds agents |
| Entry | `attune workflow run` | `AgentTeam` / `get_strategy` / templates | the agent factory |
| Output | a result | a `TeamReport` or `StrategyResult` | an agent |

Orchestration consumes agent templates and workflows and runs them; it
does not replace the per-workflow analyses — it composes them.
