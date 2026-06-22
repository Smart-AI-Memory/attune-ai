---
type: troubleshooting
feature: fix-test
depth: troubleshooting
generated_at: 2026-06-22T10:21:37.523920+00:00
source_hash: 26d8af3fe4cef200ee3e0528559c0e39b2bd3756956371d1e78427e02cb6385b
status: generated
---

# Troubleshoot fix-test

## Before you start

The fix-test feature provides test maintenance planning, coverage tracking, and source-file event handling. When tests fail unexpectedly or the system doesn't respond correctly to file changes, use this guide to diagnose and fix the issues.

## Symptom table

| If you observe | Check |
|----------------|-------|
| No plan items generated for a change | Verify the file event handler (`on_file_created/modified/deleted`) is being called with a valid path |
| Coverage tracking fails | Check that `coverage.xml` exists and is valid XML format at the expected path |
| Stale test warnings persist | Run `get_stale_tests()` to see if the detection logic matches your actual test files |
| Plan is empty or missing expected items | Inspect `plan.items` after `TestMaintenanceWorkflow.run()`; confirm the project root is correct |
| File change events ignored | Confirm the `ProjectIndex` is properly initialized and file paths are relative to project root |

## Step-by-step diagnosis

1. **Reproduce with minimal setup.**
   Create a simple test case that isolates the failing behavior. For test execution issues, try calling `run_tests_with_tracking()` directly with just the required parameters.

2. **Inspect the generated plan.**
   Call `TestMaintenanceWorkflow.run({})` and examine the returned `TestMaintenancePlan`. Look at `plan.items` for entries with unexpected `action` or `priority`, and use `get_auto_executable_items()` to see what would run automatically.

3. **Verify file path resolution.**
   Many issues stem from incorrect file paths. Ensure all paths are relative to the project root and that the `ProjectIndex` can find your test files.

4. **Test the core functions individually:**
   - `run_tests_with_tracking()` — Verify test command execution and result capture
   - `track_coverage()` — Confirm coverage.xml parsing (check file exists and has valid XML)
   - `get_file_test_status()` — Test file-to-test mapping logic
   - `TestMaintenanceWorkflow.on_file_modified()` — Verify event handling returns an appropriate `TestPlanItem`

5. **Enable debug logging.**
   Set logging level to `DEBUG` for the `attune.workflows` modules before running operations. The logs will show plan generation, file event handling, and tracking details.

## Common fixes

- **Missing coverage.xml file:** Run your test suite with coverage first: `python -m pytest --cov=src --cov-report=xml`. The `track_coverage()` function requires this file to exist.

- **Incorrect project root:** Make sure `TestMaintenanceWorkflow` resolves the absolute path to your project root, not a relative path or subdirectory.

- **Acting on the wrong items:** To run only the safe work, filter with `plan.get_auto_executable_items()` rather than executing every item — `REVIEW` and `MANUAL` actions are meant for a human.

- **Invalid test file patterns:** The system looks for files matching your project's test patterns. If using custom test discovery, ensure your test files are detectable by the `ProjectIndex`.

- **Unexpected action for a change:** If an event produces the wrong `TestAction`, review the mapping logic in the corresponding `on_file_*` handler in `test_maintenance.py`.

## Source files

- `src/attune/workflows/test_runner.py`
- `src/attune/workflows/test_maintenance.py`

**Tags:** `tests`, `debugging`, `fixes`
