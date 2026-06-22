---
type: error
feature: fix-test
depth: error
generated_at: 2026-06-22T10:21:37.523920+00:00
source_hash: 26d8af3fe4cef200ee3e0528559c0e39b2bd3756956371d1e78427e02cb6385b
status: generated
---

# Fix Test errors

Failures in test maintenance planning, test execution tracking, and source-file event handling.

## Common error signatures

- `FileNotFoundError: Coverage file not found: {path}` — The coverage.xml file specified in `track_coverage()` doesn't exist
- `ValueError: Invalid coverage.xml format: {details}` — Coverage file exists but contains malformed XML or missing required elements
- Unexpected `TestPlanItem` entries when an event maps a file to the wrong `TestAction`
- File path resolution errors when mapping source files to their corresponding test files
- Priority filtering returning nothing from `TestMaintenancePlan.get_items_by_priority()` when an invalid `TestPriority` is passed

## Where errors originate

Most failures occur during:

- **Test execution tracking** — `run_tests_with_tracking()` fails when test commands exit with non-zero codes or produce unparseable output
- **Coverage analysis** — `track_coverage()` raises exceptions when coverage files are missing, corrupted, or in unexpected formats
- **File event handling** — the handlers (`on_file_created()`, `on_file_modified()`, `on_file_deleted()`) fail when file paths are invalid or inaccessible
- **Plan generation** — `TestMaintenanceWorkflow.run()` fails when project structure analysis produces inconsistent results
- **Plan filtering** — `get_items_by_action()` / `get_items_by_priority()` return empty results when passed a value that isn't a `TestAction` / `TestPriority`

## How to diagnose

1. **Check file paths first.** Many errors stem from missing test files, moved source files, or incorrect project root configuration. Verify that the project root used by `TestMaintenanceWorkflow` points to the correct directory.

2. **Examine the plan.** If `TestMaintenanceWorkflow.run()` produces unexpected results, inspect `plan.items` and each item's `file_path`, `action`, and `metadata` for invalid or corrupted values.

3. **Validate coverage files.** When `track_coverage()` fails, check that the coverage.xml file exists and contains valid XML. The file must include `<coverage>` root elements with measurable line and branch data.

4. **Test file mapping issues.** If event handlers fail, verify that the `ProjectIndex` can correctly map source files to test files. Missing or outdated index data causes most file-based operations to fail.

5. **Check priority and action values.** `TestPlanItem` objects require valid `TestAction` and `TestPriority` enum values. Invalid enums cause filtering methods to return nothing or raise `AttributeError`.

## Source files

- `src/attune/workflows/test_runner.py`
- `src/attune/workflows/test_maintenance.py`

**Tags:** `tests`, `debugging`, `fixes`
