---
type: reference
name: fix-test-reference
feature: fix-test
depth: reference
generated_at: 2026-07-30T21:39:00.970482+00:00
source_hash: 56383ae48a3d6c0dcdadb645912bf30697dbdd296c66e69e3c40100a6c12ab69
status: generated
---

# Auto-diagnose test gaps from file changes and track test outcomes

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
