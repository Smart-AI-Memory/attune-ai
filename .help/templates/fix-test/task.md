---
feature: fix-test
depth: task
generated_at: 2026-06-22T10:21:37.523920+00:00
source_hash: 26d8af3fe4cef200ee3e0528559c0e39b2bd3756956371d1e78427e02cb6385b
status: generated
---

# Work with fix test

Use fix test when you want to extend how source-file changes are
turned into prioritized test work, or change how test outcomes are
tracked.

## Prerequisites

- Access to the project source code
- Familiarity with `src/attune/workflows/test_maintenance.py` (the
  workflow and plan model) and `src/attune/workflows/test_runner.py`
  (outcome tracking)

## Understand the two modules

| Module | Owns |
|--------|------|
| `test_maintenance.py` | `TestMaintenanceWorkflow` and the plan model — `TestPlanItem`, `TestMaintenancePlan`, `TestAction`, `TestPriority` |
| `test_runner.py` | Outcome tracking — `run_tests_with_tracking()`, `track_coverage()`, `track_file_tests()`, and the status queries |

## Generate a maintenance plan

1. **Instantiate the workflow** and call `run()` with a context dict:

   ```python
   from attune.workflows.test_maintenance import TestMaintenanceWorkflow

   workflow = TestMaintenanceWorkflow()
   plan = workflow.run({})
   ```

2. **Filter the plan** by what you need:

   ```python
   from attune.workflows.test_maintenance import TestAction, TestPriority

   to_create = plan.get_items_by_action(TestAction.CREATE)
   urgent = plan.get_items_by_priority(TestPriority.CRITICAL)
   safe = plan.get_auto_executable_items()
   ```

3. **Inspect a `TestPlanItem`** — each carries `file_path`, `action`,
   `priority`, `reason`, `test_file_path`, `estimated_effort`, and
   `auto_executable`.

## React to a single file change

Use the event handlers when you want per-file behavior rather than a
full plan:

```python
item = workflow.on_file_modified("src/attune/foo.py")
if item and item.auto_executable:
    ...
```

`on_file_created()`, `on_file_modified()`, and `on_file_deleted()`
each return a `TestPlanItem | None`.

## Track test outcomes

Use `test_runner.py` to persist what actually ran:

1. `run_tests_with_tracking(test_suite, test_files, command, workflow_id, triggered_by)` runs a suite and records the result.
2. `track_coverage(coverage_file, workflow_id)` ingests a `coverage.xml`.
3. `get_file_test_status(file_path)` and `get_files_needing_tests(stale_only, failed_only)` answer coverage questions for a file or the whole project.

## Modify behavior

- **Plan generation / prioritization** — edit `TestMaintenanceWorkflow`
  methods in `test_maintenance.py`. Adjust how an event maps to a
  `TestAction`, or how `TestPriority` is assigned.
- **New plan-item field** — add it to the `TestPlanItem` dataclass and
  update `to_dict()`.
- **Outcome tracking** — edit the tracking functions in
  `test_runner.py`.

## Verify your changes

Run the related tests:

```
pytest -k "maintenance or test_runner" tests/
```

A passing suite with no new failures confirms the plan model and
outcome tracking still behave correctly.
