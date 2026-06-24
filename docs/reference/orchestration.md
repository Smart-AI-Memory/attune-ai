# Orchestration

## Reference

### Meta-orchestration

| Symbol | Purpose |
|--------|---------|
| `MetaOrchestrator()` | `analyze_task`, `create_execution_plan`, `compose_team`, `analyze_and_compose` (all sync). |
| `TaskRequirements` / `ExecutionPlan` | Planner inputs/outputs. |
| `TaskComplexity` | `SIMPLE` / `MODERATE` / `COMPLEX`. |
| `TaskDomain` | `TESTING` / `SECURITY` / `CODE_QUALITY` / `DOCUMENTATION` / `PERFORMANCE` / `ARCHITECTURE` / `REFACTORING` / `GENERAL`. |
| `CompositionPattern` | The 10 patterns (SEQUENTIAL … DELEGATION_CHAIN). |

### Team assembly

| Symbol | Purpose |
|--------|---------|
| `get_all_templates()` / `get_template(id)` | Registry access. |
| `get_templates_by_capability(...)` / `get_templates_by_tier(...)` | Filter templates. |
| `register_custom_template(...)` / `unregister_template(...)` / `get_registry()` | Extend/inspect the registry. |
| `AgentTemplate` | `id`, `role`, `capabilities`, `tools`, `tier_preference`, `quality_gates`, `resource_requirements`. |
| `AgentCapability` / `ResourceRequirements` | Capability + resource models. |
| `DynamicTeamBuilder(state_store=None, redis_client=None)` | `build_from_spec` / `build_from_plan` / `build_from_config`. |
| `DynamicTeam` / `DynamicTeamResult` / `TeamSpecification` / `TeamStore` | Team objects + persistence. |

### Execution & composition

| Symbol | Purpose |
|--------|---------|
| `ExecutionStrategy` | Base; `execute(agents, context)` is **async** → `StrategyResult`. |
| `get_strategy(name)` | Resolve a no-arg strategy (9 names). `conditional`/`multi_conditional`/`nested`/`nested_sequential` are registered too but need constructor args. |
| `ToolEnhancedStrategy` / `PromptCachedSequentialStrategy` / `DelegationChainStrategy` | Exported concrete strategies. |
| `WorkflowComposer(state_store=None)` | `compose` / `compose_with_simplification`. |
| `WorkflowAgentAdapter` | Run a workflow as a team agent. |

<!-- attune-generated: source_hash=8eeb348f730d4eaa712d0cf9b78905ce878837e5c821fc161778c91d1d163103 feature=orchestration kind=reference generated_at=2026-06-24 -->
