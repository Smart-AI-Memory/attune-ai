# Fix Test

## Quickstart

**Fastest path — `/fix-test` in Claude Code.** For an interactive
fix, run `/fix-test <test file or pattern>` in a Claude Code
session — it scopes the target, classifies the root cause, applies
a fix, and re-runs (up to 3 attempts) before reporting. The full
walkthrough, including wiring a tests-on-edit hook so failures are
caught and fixed the moment an edit creates them, is the tutorial
at `docs/tutorials/fix-test.md`.

For the Python API, generate a maintenance plan for the whole project.
`TestMaintenanceWorkflow.run` is an async coroutine, so drive it with
`asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.workflows import TestMaintenanceWorkflow


async def main() -> None:
    workflow = TestMaintenanceWorkflow(project_root=".")
    result = await workflow.run({"mode": "analyze"})
    print(result["status"])               # "plan_generated"
    print(result["message"])              # "Generated plan with N items"
    for item in result["plan"]["items"]:
        print(item["priority"], item["action"], item["file_path"])


asyncio.run(main())
```

`run` returns a plain dict (the plan is `result["plan"]`, already
serialized via `TestMaintenancePlan.to_dict`). The `"analyze"` mode
only *plans* — it never writes tests. Use `"auto"` to execute the
items flagged `auto_executable`, or `"report"` for a health summary.

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

## Reference

Fix-test's public API spans two workflow modules. The record types
(`TestExecutionRecord`, `CoverageRecord`, `FileTestRecord`) come from
`attune.models`.

### Planning — `attune.workflows.test_maintenance`

| Symbol | Purpose |
|--------|---------|
| `TestMaintenanceWorkflow(project_root, index=None)` | Coordinator. Builds (or accepts) a `ProjectIndex` and ensures it is loaded. |
| `TestMaintenanceWorkflow.run(context)` | **Async.** Generate (and optionally execute) a plan. `context["mode"]` is `"analyze"` / `"execute"` / `"auto"` / `"report"`; other keys: `changed_files`, `max_items` (default 20), `dry_run` (default `False`). Returns a result dict. |
| `TestMaintenanceWorkflow.on_file_created(file_path)` | **Async.** Plan test work for a new file; returns a status dict. |
| `TestMaintenanceWorkflow.on_file_modified(file_path)` | **Async.** Mark a changed file's tests as possibly stale; returns a status dict. |
| `TestMaintenanceWorkflow.on_file_deleted(file_path)` | **Async.** Flag a deleted file's tests as possibly orphaned; returns a status dict. |
| `TestMaintenanceWorkflow.get_files_needing_tests(limit=20)` | Top-`limit` files needing tests, by impact, as dicts. |
| `TestMaintenanceWorkflow.get_stale_tests(limit=20)` | Top-`limit` files with stale tests, by staleness, as dicts. |
| `TestMaintenanceWorkflow.get_test_health_summary()` | Quick counts: files requiring/with/without tests, average coverage, stale count, test-to-code ratio. |
| `TestMaintenancePlan.get_items_by_action(action)` | Plan items filtered by a `TestAction`. |
| `TestMaintenancePlan.get_items_by_priority(priority)` | Plan items filtered by a `TestPriority`. |
| `TestMaintenancePlan.get_auto_executable_items()` | Plan items with `auto_executable=True`. |
| `TestAction` | Enum: `CREATE`, `UPDATE`, `REVIEW`, `DELETE`, `SKIP`, `MANUAL`. |
| `TestPriority` | Enum: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `DEFERRED`. |

### Measurement — `attune.workflows.test_runner`

| Symbol | Purpose |
|--------|---------|
| `run_tests_with_tracking(test_suite="unit", test_files=None, command=None, workflow_id=None, triggered_by="manual")` | Run a suite and persist a `TestExecutionRecord`. |
| `track_coverage(coverage_file="coverage.xml", workflow_id=None)` | Parse a coverage XML file into a `CoverageRecord`. Raises `FileNotFoundError` / `ValueError`. |
| `track_file_tests(source_file, test_file=None, workflow_id=None)` | Run a single file's tests and persist a `FileTestRecord`. |
| `get_file_test_status(file_path)` | Latest `FileTestRecord` for a file, or `None`. |
| `get_files_needing_tests(stale_only=False, failed_only=False)` | `FileTestRecord` list for files needing attention (telemetry-backed; **not** the workflow method of the same name). |

### TestPlanItem fields

| Field | Type | Meaning |
|-------|------|---------|
| `file_path` | `str` | The source file this item concerns. |
| `action` | `TestAction` | What to do with the test. |
| `priority` | `TestPriority` | How urgent. |
| `reason` | `str` | Why this item exists. |
| `test_file_path` | `str \| None` | The associated test file, if known. |
| `estimated_effort` | `str` | Effort hint (default `"unknown"`). |
| `auto_executable` | `bool` | Whether `"auto"` mode may run it (default `True`). |
| `metadata` | `dict` | Free-form extra context. |

<!-- attune-generated: source_hash=56383ae48a3d6c0dcdadb645912bf30697dbdd296c66e69e3c40100a6c12ab69 feature=fix-test kind=how-to generated_at=2026-07-30 -->
