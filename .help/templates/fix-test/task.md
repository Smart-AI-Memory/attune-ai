---
type: task
name: fix-test-task
feature: fix-test
depth: task
generated_at: 2026-07-30T21:39:00.970482+00:00
source_hash: 56383ae48a3d6c0dcdadb645912bf30697dbdd296c66e69e3c40100a6c12ab69
status: generated
---

# Auto-diagnose test gaps from file changes and track test outcomes

## Tasks

### React to a single file change

**Goal:** translate one file event into the test work it implies —
the hook into a file-watcher or git hook.

**Steps:**

```python
import asyncio

from attune.workflows import TestMaintenanceWorkflow


async def main() -> None:
    workflow = TestMaintenanceWorkflow(project_root=".")

    created = await workflow.on_file_created("src/attune/new_module.py")
    print(created["status"])      # e.g. "needs_tests" or "no_tests_required"

    modified = await workflow.on_file_modified("src/attune/config.py")
    print(modified["status"])     # e.g. "tests_may_need_update"

    deleted = await workflow.on_file_deleted("src/attune/old_module.py")
    print(deleted["status"])      # e.g. "orphaned_tests" or "file_removed"


asyncio.run(main())
```

**Verify:** each handler is a coroutine — `await` it. Each returns a
dict whose `status` names the outcome and (when relevant) carries a
`plan_item` built from a `TestPlanItem`. A created file that requires
tests reports `"needs_tests"`; a deleted file whose test file still
exists reports `"orphaned_tests"`.

### Auto-execute only the safe items

**Goal:** run the test work that is safe to run unattended, and leave
higher-touch items for a human.

**Steps:**

```python
import asyncio

from attune.workflows import TestMaintenanceWorkflow


async def main() -> None:
    workflow = TestMaintenanceWorkflow(project_root=".")

    # Preview first — dry_run plans without executing.
    preview = await workflow.run({"mode": "auto", "dry_run": True})
    print(preview["message"])     # "Would auto-execute N items"

    # Then execute the auto_executable subset.
    result = await workflow.run({"mode": "auto"})
    print(result["status"])       # "auto_executed"
    print(result["execution"])    # per-item execution outcomes


asyncio.run(main())
```

**Verify:** `"auto"` mode executes only the items
`TestMaintenancePlan.get_auto_executable_items` returns (those with
`auto_executable=True`). `dry_run=True` reports the count without
executing. Items needing `REVIEW` or `MANUAL` are never auto-run.

### Track a test run and read coverage back

**Goal:** record a suite execution and its coverage so the workflow
can reason about gaps later.

**Steps:**

```python
from attune.workflows.test_runner import (
    run_tests_with_tracking,
    track_coverage,
    get_file_test_status,
)

# Run a suite and persist a TestExecutionRecord.
execution = run_tests_with_tracking(
    test_suite="unit",
    test_files=["tests/unit/test_config.py"],
    triggered_by="manual",
)
print(execution.success, execution.passed, execution.failed)

# Parse an existing coverage.xml into a CoverageRecord.
coverage = track_coverage("coverage.xml")
print(f"{coverage.overall_percentage:.1f}%")

# Read the latest status for one file.
status = get_file_test_status("src/attune/config.py")
print(status)                     # FileTestRecord | None
```

**Verify:** these are plain (synchronous) functions — no `await`.
`run_tests_with_tracking` returns a `TestExecutionRecord` (`success`,
`passed`, `failed`); `track_coverage` returns a `CoverageRecord` and
raises `FileNotFoundError` if `coverage.xml` is missing or `ValueError`
if it is malformed; `get_file_test_status` returns the latest
`FileTestRecord` for a file, or `None` if nothing was recorded.
