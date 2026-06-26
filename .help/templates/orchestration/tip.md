---
type: tip
name: orchestration-tip
feature: orchestration
depth: tip
generated_at: 2026-06-26T16:19:58.397279+00:00
source_hash: 3da859c638c01505e80876fc298c0d02f94889242bbb1c93df05af5291945567
status: generated
---

# Reusable agent templates, a library of execution strategies, and parallel agent teams with quality gates

## Notes & tips

- **Await the run.** `AgentTeam.run` and `execute` are async.
- **Start from templates.** `get_all_templates()` is the cheapest way to
  see what a team can be built from.
- **`get_strategy` takes a registry name**, not a class.
- **`AgentTeam` is fan-out + gate**, not a planner — you pick the agents
  and the gates.
