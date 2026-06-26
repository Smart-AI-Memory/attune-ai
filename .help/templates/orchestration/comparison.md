---
type: comparison
name: orchestration-comparison
feature: orchestration
depth: comparison
generated_at: 2026-06-26T16:19:58.397279+00:00
source_hash: 3da859c638c01505e80876fc298c0d02f94889242bbb1c93df05af5291945567
status: generated
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
