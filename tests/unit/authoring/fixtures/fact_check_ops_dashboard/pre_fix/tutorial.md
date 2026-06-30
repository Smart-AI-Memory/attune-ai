# Tutorial: extending the ops dashboard

A walkthrough of adding a custom panel to the ops dashboard.

## Read the run state

The ``RunsReader`` class loads persisted run records from disk
and yields them sorted by completion time.

```python
from attune.ops._readers import RunsReader

reader = RunsReader()
for run in reader.iter_completed(limit=20):
    print(run.id, run.status)
```

## Construct a Run record manually

For tests or scripted seeding, build a ``RunRecord`` directly:

```python
from attune.ops._models import RunRecord

record = RunRecord(
    id="abc123",
    workflow="release-prep",
    status="completed",
)
```

## Render a panel

Panels render to the structured report area above the process
log.

```python
from attune.workflows.output import WorkflowReport, CalloutSection

report = WorkflowReport(
    title="Custom panel",
    sections=[
        CalloutSection(
            title="Status",
            tier="essential",
            text="All systems green",
            emphasis="ok",
        ),
    ],
)
```

## See also

- [Reference: Run API endpoints](../reference/run-api.md)
- [Concept: Template design patterns](../concepts/template-design-patterns.md)
