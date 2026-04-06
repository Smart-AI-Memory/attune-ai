---
feature: fix-test
depth: reference
generated_at: 2026-04-06T04:29:46.364946+00:00
source_hash: add950818a88e621df7bd12cd03ded18fe60e40bac9a1bae6eb24fe1ff69abc8
status: generated
---

# Fix Test reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `TestAction` | Defines actions you can take for test management workflows. | `src/attune/workflows/test_maintenance.py` |
| `TestPriority` | Sets priority levels for test maintenance actions. | `src/attune/workflows/test_maintenance.py` |
| `TestPlanItem` | Represents a single item in a test maintenance plan. | `src/attune/workflows/test_maintenance.py` |
| `TestMaintenancePlan` | Provides a complete test maintenance plan for your project. | `src/attune/workflows/test_maintenance.py` |
| `TestMaintenanceWorkflow` | Automates test lifecycle management through event-driven workflows. | `src/attune/workflows/test_maintenance.py` |
| `TestTask` | Represents a queued test management task in the workflow. | `src/attune/workflows/test_lifecycle.py` |
| `TestLifecycleManager` | Manages test lifecycles based on source file change events. | `src/attune/workflows/test_lifecycle.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `run_tests_with_tracking()` | Runs tests with explicit tracking for Tier 1 automation monitoring. | `src/attune/workflows/test_runner.py` |
| `track_coverage()` | Tracks test coverage metrics from coverage.xml files for Tier 1 monitoring. | `src/attune/workflows/test_runner.py` |
| `track_file_tests()` | Tracks test execution results for a specific source file. | `src/attune/workflows/test_runner.py` |
| `get_file_test_status()` | Retrieves the latest test status for a specific file. | `src/attune/workflows/test_runner.py` |
| `get_files_needing_tests()` | Identifies files that require test attention or updates. | `src/attune/workflows/test_runner.py` |


## Source files

- `src/attune/workflows/test_runner.py`
- `src/attune/workflows/test_maintenance.py`
- `src/attune/workflows/test_lifecycle.py`

## Tags

`tests`, `debugging`, `fixes`
