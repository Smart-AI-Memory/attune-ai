---
name: session-handoff
source: content/features/session-handoff.md
tags:
- handoff
- collaboration
- multi-llm
- memory
type: task
---

# Cross-provider session handoff — verified packet create/resume so any agent can pick up a branch mid-flight

## Tasks

### Create a handoff packet for the current branch

```python
from attune.handoff import handoff_create

result = handoff_create(
    ".",
    goal="What should be true when this work is complete",
    acceptance_criteria="Concrete completion conditions",
    current_state="Status, decisions, risks",
    next_action="One concrete ordered action",
    provider="claude-code",
)
assert result["ok"], result
print(result["path"])  # docs/handoffs/<branch-slug>.md
```

### Resume a packet and read the drift report

```python
from attune.handoff import handoff_resume

report = handoff_resume(".")
if report["ok"]:
    for warning in report["warnings"]:
        print(warning["code"], warning["detail"])
```

### Record verification claims without fabricating results

```python
from attune.handoff import handoff_create

handoff_create(
    ".",
    goal="Land the fix",
    verification=[{"claim": "unit suite green", "probe": "pytest -q tests/unit"}],
)
# The stored row's result is "not run" — the receiver re-runs probes.
```
