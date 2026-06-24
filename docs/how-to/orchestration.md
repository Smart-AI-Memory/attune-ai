# Orchestration

## Quickstart

Inspect the agent templates and grab a strategy:

```python
from attune.orchestration import get_all_templates, get_strategy

templates = get_all_templates()
print(len(templates), "templates; e.g.", templates[0].id)

strategy = get_strategy("sequential")
print(type(strategy).__name__)
```

## Tasks

### Analyze a task and plan its orchestration

```python
from attune.orchestration import MetaOrchestrator

orch = MetaOrchestrator()
reqs = orch.analyze_task("audit security and add tests")
print(reqs.complexity, reqs.domain)
```

**Verify:** `analyze_task(...)` is synchronous and returns a
`TaskRequirements` with a `complexity` (`TaskComplexity`) and `domain`
(`TaskDomain`). `create_execution_plan(...)` turns that into an
`ExecutionPlan`.

### Find agent templates by capability or tier

```python
from attune.orchestration import (
    get_all_templates,
    get_template,
    get_templates_by_tier,
)

all_templates = get_all_templates()
one = get_template(all_templates[0].id)
print(one.role, [str(c) for c in one.capabilities])
```

**Verify:** `get_all_templates()` returns the registry's templates;
`get_template(template_id)` returns one (or `None`);
`get_templates_by_capability` / `get_templates_by_tier` filter the set.

### Pick an execution strategy

```python
from attune.orchestration import get_strategy

strategy = get_strategy("parallel")
print(type(strategy).__name__)
```

**Verify:** `get_strategy(name)` resolves the nine no-arg strategy names
above to a strategy. Running it — `await strategy.execute(agents,
context)` — is **async** and returns a `StrategyResult`.

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

<!-- attune-generated: source_hash=8eeb348f730d4eaa712d0cf9b78905ce878837e5c821fc161778c91d1d163103 feature=orchestration kind=how-to generated_at=2026-06-24 -->
