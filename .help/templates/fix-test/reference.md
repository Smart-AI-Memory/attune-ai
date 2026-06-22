---
feature: fix-test
depth: reference
generated_at: 2026-06-22T10:21:37.523920+00:00
source_hash: 26d8af3fe4cef200ee3e0528559c0e39b2bd3756956371d1e78427e02cb6385b
status: generated
---

# Fix Test reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `TestAction` | Action to take for a test: `CREATE`, `UPDATE`, `REVIEW`, `DELETE`, `SKIP`, `MANUAL`. | `src/attune/workflows/test_maintenance.py` |
| `TestPriority` | Priority for a test action: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `DEFERRED`. | `src/attune/workflows/test_maintenance.py` |
| `TestPlanItem` | A single item in a test maintenance plan. | `src/attune/workflows/test_maintenance.py` |
| `TestMaintenancePlan` | Complete test maintenance plan for a project. | `src/attune/workflows/test_maintenance.py` |
| `TestMaintenanceWorkflow` | Coordinates test maintenance from source-file events. | `src/attune/workflows/test_maintenance.py` |

### `TestPlanItem` fields

| Field | Type | Role |
|-------|------|------|
| `file_path` | `str` | The source file the work concerns |
| `action` | `TestAction` | What to do with the test |
| `priority` | `TestPriority` | How urgent the work is |
| `reason` | `str` | Why this item was generated |
| `test_file_path` | `str \| None` | The associated test file, if known |
| `estimated_effort` | `str` | Rough effort estimate |
| `auto_executable` | `bool` | Whether the item can be run without review |
| `metadata` | `dict` | Free-form extra context |

`to_dict()` serializes the item.

### `TestMaintenancePlan` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict()` | — | `dict` | Serialize the plan. |
| `get_items_by_action(action)` | `action: TestAction` | `list[TestPlanItem]` | Items with the given action. |
| `get_items_by_priority(priority)` | `priority: TestPriority` | `list[TestPlanItem]` | Items at the given priority. |
| `get_auto_executable_items()` | — | `list[TestPlanItem]` | Items safe to run automatically. |

Fields: `generated_at`, `items`, `summary`, `options`.

### `TestMaintenanceWorkflow` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `run(context)` | `context: dict` | `TestMaintenancePlan` | Build a maintenance plan for the project. |
| `on_file_created(file_path)` | `file_path: str` | `TestPlanItem \| None` | Test work implied by a new file. |
| `on_file_modified(file_path)` | `file_path: str` | `TestPlanItem \| None` | Test work implied by a changed file. |
| `on_file_deleted(file_path)` | `file_path: str` | `TestPlanItem \| None` | Test work implied by a deleted file. |
| `get_files_needing_tests(limit)` | `limit: int` | `list` | Files needing tests, prioritized by impact. |
| `get_stale_tests(limit)` | `limit: int` | `list` | Files with stale tests. |
| `get_test_health_summary()` | — | `dict` | Quick test-health summary. |

## Functions

| Function | Parameters | Returns | Description | File |
|----------|------------|---------|-------------|------|
| `run_tests_with_tracking()` | `test_suite, test_files, command, workflow_id, triggered_by` | `dict` | Run tests with explicit tracking (opt-in Tier 1 monitoring). | `test_runner.py` |
| `track_coverage()` | `coverage_file, workflow_id` | `dict` | Track coverage from a `coverage.xml` file. | `test_runner.py` |
| `track_file_tests()` | `source_file, test_file, workflow_id` | `dict` | Track test execution for a specific source file. | `test_runner.py` |
| `get_file_test_status()` | `file_path` | `FileTestRecord \| None` | Latest test status for a file. | `test_runner.py` |
| `get_files_needing_tests()` | `stale_only, failed_only` | `list` | Files that need test attention. | `test_runner.py` |

## Source files

- `src/attune/workflows/test_runner.py`
- `src/attune/workflows/test_maintenance.py`

## Tags

`tests`, `debugging`, `fixes`
