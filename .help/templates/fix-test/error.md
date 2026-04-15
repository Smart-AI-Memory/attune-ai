---
type: error
feature: fix-test
depth: error
generated_at: 2026-04-14T14:56:45.083008+00:00
source_hash: add950818a88e621df7bd12cd03ded18fe60e40bac9a1bae6eb24fe1ff69abc8
status: generated
---

# Fix Test errors

Failures in automated test lifecycle management, test execution tracking, and test maintenance workflows.

## Common error signatures

- `FileNotFoundError: Coverage file not found: {path}` — The coverage.xml file specified in `track_coverage()` doesn't exist
- `ValueError: Invalid coverage.xml format: {details}` — Coverage file exists but contains malformed XML or missing required elements
- Test task queue corruption causing `TestTask` processing failures
- File path resolution errors when mapping source files to their corresponding test files
- Priority filtering failures in `TestLifecycleManager.process_queue()`

## Where errors originate

Most failures occur during:

- **Test execution tracking** — `run_tests_with_tracking()` fails when test commands exit with non-zero codes or produce unparseable output
- **Coverage analysis** — `track_coverage()` raises exceptions when coverage files are missing, corrupted, or in unexpected formats
- **File monitoring** — Event handlers (`on_file_created()`, `on_file_modified()`, `on_file_deleted()`) fail when file paths are invalid or inaccessible
- **Queue processing** — `TestLifecycleManager.process_queue()` encounters errors when tasks reference deleted files or have malformed metadata
- **Test maintenance planning** — `TestMaintenanceWorkflow.run()` fails when project structure analysis produces inconsistent results

## How to diagnose

1. **Check file paths first.** Many errors stem from missing test files, moved source files, or incorrect project root configuration. Verify that `project_root` in `TestMaintenanceWorkflow` and `TestLifecycleManager` points to the correct directory.

2. **Examine the task queue.** If `TestLifecycleManager` operations fail, call `get_queue()` to inspect pending tasks. Look for tasks with invalid `file_path` values or corrupted `metadata` fields.

3. **Validate coverage files.** When `track_coverage()` fails, check that the coverage.xml file exists and contains valid XML. The file must include `<coverage>` root elements with measurable line and branch data.

4. **Test file mapping issues.** If test lifecycle events fail, verify that the `ProjectIndex` can correctly map source files to test files. Missing or outdated index data causes most file-based operations to fail.

5. **Check priority and action values.** `TestPlanItem` and `TestTask` objects require valid `TestAction` and `TestPriority` enum values. Invalid enums cause filtering and processing methods to raise `AttributeError` or `KeyError`.

## Source files

- `src/attune/workflows/test_runner.py`
- `src/attune/workflows/test_maintenance.py`
- `src/attune/workflows/test_lifecycle.py`

**Tags:** `tests`, `debugging`, `fixes`
