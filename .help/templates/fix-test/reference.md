---
feature: fix-test
depth: reference
generated_at: 2026-04-13T16:56:32.672502+00:00
source_hash: add950818a88e621df7bd12cd03ded18fe60e40bac9a1bae6eb24fe1ff69abc8
status: generated
---

# Fix Test reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `TestAction` | Actions that can be taken for test management. | `src/attune/workflows/test_maintenance.py` |
| `TestPriority` | Priority levels for test actions. | `src/attune/workflows/test_maintenance.py` |
| `TestPlanItem` | A single item in a test maintenance plan. | `src/attune/workflows/test_maintenance.py` |
| `TestMaintenancePlan` | Complete test maintenance plan for a project. | `src/attune/workflows/test_maintenance.py` |
| `TestMaintenanceWorkflow` | Event-driven workflow for automatic test lifecycle management. | `src/attune/workflows/test_maintenance.py` |
| `TestTask` | A queued test management task. | `src/attune/workflows/test_lifecycle.py` |
| `TestLifecycleManager` | Event-driven manager that handles test lifecycle based on source file changes. | `src/attune/workflows/test_lifecycle.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `run_tests_with_tracking()` | Runs tests with explicit tracking for Tier 1 automation monitoring. | `src/attune/workflows/test_runner.py` |
| `track_coverage()` | Tracks test coverage from coverage.xml file for Tier 1 automation monitoring. | `src/attune/workflows/test_runner.py` |
| `track_file_tests()` | Tracks test execution for a specific source file. | `src/attune/workflows/test_runner.py` |
| `get_file_test_status()` | Returns the latest test status for a specific file. | `src/attune/workflows/test_runner.py` |
| `get_files_needing_tests()` | Returns files that need test attention. | `src/attune/workflows/test_runner.py` |

## Source files

- `src/attune/workflows/test_runner.py`
- `src/attune/workflows/test_maintenance.py`
- `src/attune/workflows/test_lifecycle.py`

## Tags

`tests`, `debugging`, `fixes`
