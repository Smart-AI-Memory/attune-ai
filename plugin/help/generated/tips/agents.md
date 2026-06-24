---
name: agents
source: content/features/agents.md
tags:
- agents
- ai
type: tip
---

# Universal Agent Factory — create, run, and orchestrate AI agents across frameworks

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  `AgentFactory`, `Framework`, `BaseAdapter`, `BaseAgent`,
  `AgentConfig`, `WorkflowConfig`, `AgentRole`, and `AgentCapability`
  from `attune.agent_factory`. Framework-specific adapter/agent classes
  are internal.
- **`await` the run methods.** Only `invoke` / `run` / `stream` are
  async; the `create_*` builders are sync.
- **Start native.** The `native` framework needs no extra deps; reach
  for LangChain/LangGraph/AutoGen/Haystack when you need their
  features.
- **Use role presets and pipelines.** `create_researcher()` /
  `create_research_pipeline()` are faster than wiring configs by hand.
