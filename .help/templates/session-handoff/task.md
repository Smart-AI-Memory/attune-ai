---
type: task
name: session-handoff-task
feature: session-handoff
depth: task
generated_at: 2026-07-28T03:00:44.232722+00:00
source_hash: 963aaf0dd059e464542f852a8b8c1f93be3beb0bbf89675536ba711fe6d47c66
status: generated
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
