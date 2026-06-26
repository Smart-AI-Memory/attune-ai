---
name: orchestration
source: content/features/orchestration.md
tags:
- orchestration
- teams
type: tip
---

# Reusable agent templates, a library of execution strategies, and parallel agent teams with quality gates

## Notes & tips

- **Await the run.** `AgentTeam.run` and `execute` are async.
- **Start from templates.** `get_all_templates()` is the cheapest way to
  see what a team can be built from.
- **`get_strategy` takes a registry name**, not a class.
- **`AgentTeam` is fan-out + gate**, not a planner — you pick the agents
  and the gates.
