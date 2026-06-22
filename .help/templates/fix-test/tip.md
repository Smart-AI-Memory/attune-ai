---
type: tip
feature: fix-test
depth: tip
generated_at: 2026-06-22T10:21:37.523920+00:00
source_hash: 26d8af3fe4cef200ee3e0528559c0e39b2bd3756956371d1e78427e02cb6385b
status: generated
---

# Use TestMaintenanceWorkflow for event-driven test maintenance

Reach for `TestMaintenanceWorkflow` when files change in your project — its event handlers turn each change into a `TestPlanItem` describing the test action that change implies.

## Why this matters

Letting the workflow map changes to test actions is faster than manually tracking which tests need updates every time you modify source code.

## How to use it

Call the handler that matches the change, then act on the returned item:

```python
from attune.workflows.test_maintenance import TestMaintenanceWorkflow

workflow = TestMaintenanceWorkflow()

# When a file is created, modified, or deleted
item = workflow.on_file_created("src/new_module.py")
item = workflow.on_file_modified("src/existing_module.py")
item = workflow.on_file_deleted("src/old_module.py")

# Or build a full plan and run only the safe items
plan = workflow.run({})
safe = plan.get_auto_executable_items()
```

## The tradeoff

`run()` produces a plan rather than executing everything — you get control over what runs, but you decide which items to act on. Use `get_auto_executable_items()` for the safe subset and leave `REVIEW`/`MANUAL` items for a human.
