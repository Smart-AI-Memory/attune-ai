# Orchestration

## Reference

### Team templates

| Symbol | Purpose |
|--------|---------|
| `get_all_templates()` / `get_template(id)` | Registry access. |
| `get_templates_by_capability(...)` / `get_templates_by_tier(...)` | Filter templates. |
| `register_custom_template(...)` / `unregister_template(...)` / `get_registry()` | Extend/inspect the registry. |
| `AgentTemplate` | `id`, `role`, `capabilities`, `tools`, `tier_preference`, `quality_gates`, `resource_requirements`. |
| `AgentCapability` / `ResourceRequirements` | Capability + resource models. |

### Agent teams

`AgentTeam` (`attune.agents.team`) fans out workflow agents over a
target and applies score gates. It is fan-out + gate only — no
sequential, two-phase, or DAG topology.

| Symbol | Purpose |
|--------|---------|
| `AgentTeam(agents, gates)` | `run(target)` is **async** → `TeamReport`. |
| `WorkflowAgent(key, workflow_cls, *, files=None, score_fn=None, default_score=None, escalate=False)` | Wrap a workflow as a team agent. |
| `GateSpec(name, agent_key, threshold, critical=True)` | Pass/fail gate on an agent's score. |
| `TeamReport` | `passed`, `gates`, `results`, `blockers`, `warnings`, `cost`. |
| `AgentResult` | `key`, `score`, `cost`, `success`, `details`. |

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

### Execution strategies

| Symbol | Purpose |
|--------|---------|
| `ExecutionStrategy` | Base; `execute(agents, context)` is **async** → `StrategyResult`. |
| `get_strategy(name)` | Resolve a no-arg strategy (9 names). `conditional`/`multi_conditional`/`nested`/`nested_sequential` are registered too but need constructor args. |
| `ToolEnhancedStrategy` / `PromptCachedSequentialStrategy` / `DelegationChainStrategy` | Exported concrete strategies. |

<!-- attune-generated: source_hash=8eeb348f730d4eaa712d0cf9b78905ce878837e5c821fc161778c91d1d163103 feature=orchestration kind=reference generated_at=2026-06-24 -->
