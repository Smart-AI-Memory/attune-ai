---
name: orchestration
source: content/features/orchestration.md
tags:
- orchestration
- teams
type: reference
---

# Reusable agent templates, a library of execution strategies, and parallel agent teams with quality gates

## Reference

### Agent teams

| Symbol | Purpose |
|--------|---------|
| `AgentTeam(agents, gates)` | Fan-out + gate runner; `await run(target)` → `TeamReport`. |
| `WorkflowAgent(key, workflow_cls, *, files=...)` | Wrap a workflow as a scored agent. |
| `GateSpec(name, agent_key, threshold, critical=True)` | Threshold one agent's score; `critical=False` → warning, not blocker. |
| `TeamReport` | `passed`, `gates`, `results`, `blockers`, `warnings`, `cost`. |
| `AgentResult` | Per-agent `key`, `score`, `cost`, `success`, `details`. |

### Agent templates

| Symbol | Purpose |
|--------|---------|
| `get_all_templates()` / `get_template(id)` | Registry access. |
| `get_templates_by_capability(...)` / `get_templates_by_tier(...)` | Filter templates. |
| `register_custom_template(...)` / `unregister_template(...)` / `get_registry()` | Extend/inspect the registry. |
| `AgentTemplate` | `id`, `role`, `capabilities`, `tools`, `tier_preference`, `quality_gates`, `resource_requirements`. |
| `AgentCapability` / `ResourceRequirements` | Capability + resource models. |

### Execution strategies

| Symbol | Purpose |
|--------|---------|
| `ExecutionStrategy` | Base; `execute(agents, context)` is **async** → `StrategyResult`. |
| `get_strategy(name)` | Resolve a no-arg strategy (9 names). `conditional`/`multi_conditional`/`nested`/`nested_sequential` are registered too but need constructor args. |
| `ToolEnhancedStrategy` / `PromptCachedSequentialStrategy` / `DelegationChainStrategy` | Exported concrete strategies. |
