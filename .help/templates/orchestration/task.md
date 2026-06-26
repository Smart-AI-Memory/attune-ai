---
type: task
name: orchestration-task
feature: orchestration
depth: task
generated_at: 2026-06-26T16:19:58.397279+00:00
source_hash: 3da859c638c01505e80876fc298c0d02f94889242bbb1c93df05af5291945567
status: generated
---

# Reusable agent templates, a library of execution strategies, and parallel agent teams with quality gates

## Tasks

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
print(report.passed, report.blockers, report.warnings)
```

**Verify:** `team.run(target)` is **async** and returns a `TeamReport`
with `passed`, `blockers`, `warnings`, `results`, and `cost`.

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
