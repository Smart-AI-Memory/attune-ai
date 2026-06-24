---
type: tip
name: orchestration-tip
feature: orchestration
depth: tip
generated_at: 2026-06-24T04:42:36.420317+00:00
source_hash: 8eeb348f730d4eaa712d0cf9b78905ce878837e5c821fc161778c91d1d163103
status: generated
---

# Dynamic agent teams, workflow composition, and meta-orchestration of multi-agent pipelines

## Notes & tips

- **Plan sync, execute async.** `MetaOrchestrator` / builders are sync;
  `execute` is async.
- **Start from templates.** `get_all_templates()` is the cheapest way to
  see what a team can be built from.
- **`get_strategy` takes a registry name**, not a class.
- **Orchestration composes workflows; it doesn't replace them.**
