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

### Run a multi-agent quality gate

```python
import asyncio
from attune.agents.team import AgentTeam, GateSpec, WorkflowAgent
from attune.workflows.code_review import CodeReviewWorkflow
from attune.workflows.security_audit import SecurityAuditWorkflow

team = AgentTeam(
    agents=[
        WorkflowAgent("code-review", CodeReviewWorkflow, files=["src/"]),
        WorkflowAgent("security-audit", SecurityAuditWorkflow, files=["src/"]),
    ],
    gates=[
        GateSpec("Code Quality", "code-review", 80.0),
        GateSpec("Security", "security-audit", 80.0),
    ],
)
report = asyncio.run(team.run(["src/"]))
print(report.passed, report.blockers, report.warnings, report.cost)
```

**Verify:** `AgentTeam` fans out each `WorkflowAgent` over the target,
then applies the `GateSpec` thresholds. `team.run(target)` is **async**
and returns a `TeamReport` (`passed`, `gates`, `results`, `blockers`,
`warnings`, `cost`). This is fan-out + gate only — no sequential,
two-phase, or DAG topology.

## Reference

### Team assembly

| Symbol | Purpose |
|--------|---------|
| `get_all_templates()` / `get_template(id)` | Registry access. |
| `get_templates_by_capability(...)` / `get_templates_by_tier(...)` | Filter templates. |
| `register_custom_template(...)` / `unregister_template(...)` / `get_registry()` | Extend/inspect the registry. |
| `AgentTemplate` | `id`, `role`, `capabilities`, `tools`, `tier_preference`, `quality_gates`, `resource_requirements`. |
| `AgentCapability` / `ResourceRequirements` | Capability + resource models. |

### Multi-agent quality gates

| Symbol | Purpose |
|--------|---------|
| `AgentTeam(agents, gates)` | Fan-out + gate runner. `run(target)` is **async** → `TeamReport`. |
| `WorkflowAgent(key, workflow_cls, *, files=None, score_fn=None, default_score=None, escalate=False)` | Wrap a workflow as a team agent. |
| `GateSpec(name, agent_key, threshold, critical=True)` | Threshold gate over one agent's score. |
| `TeamReport` | `passed`, `gates`, `results`, `blockers`, `warnings`, `cost`. |
| `AgentResult` | `key`, `score`, `cost`, `success`, `details`. |

### Execution strategies

| Symbol | Purpose |
|--------|---------|
| `ExecutionStrategy` | Base; `execute(agents, context)` is **async** → `StrategyResult`. |
| `get_strategy(name)` | Resolve a no-arg strategy (9 names). `conditional`/`multi_conditional`/`nested`/`nested_sequential` are registered too but need constructor args. |
| `ToolEnhancedStrategy` / `PromptCachedSequentialStrategy` / `DelegationChainStrategy` | Exported concrete strategies. |

<!-- attune-generated: source_hash=8eeb348f730d4eaa712d0cf9b78905ce878837e5c821fc161778c91d1d163103 feature=orchestration kind=how-to generated_at=2026-06-24 -->
