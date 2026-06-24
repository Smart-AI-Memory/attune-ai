---
name: orchestration
source: content/features/orchestration.md
tags:
- orchestration
- teams
type: tip
---

# Dynamic agent teams, workflow composition, and meta-orchestration of multi-agent pipelines

## Notes & tips

- **Plan sync, execute async.** `MetaOrchestrator` / builders are sync;
  `execute` is async.
- **Start from templates.** `get_all_templates()` is the cheapest way to
  see what a team can be built from.
- **`get_strategy` takes a registry name**, not a class.
- **Orchestration composes workflows; it doesn't replace them.**
