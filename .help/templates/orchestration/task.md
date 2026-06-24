---
type: task
name: orchestration-task
feature: orchestration
depth: task
generated_at: 2026-06-24T04:42:36.420317+00:00
source_hash: 8eeb348f730d4eaa712d0cf9b78905ce878837e5c821fc161778c91d1d163103
status: generated
---

# Dynamic agent teams, workflow composition, and meta-orchestration of multi-agent pipelines

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
