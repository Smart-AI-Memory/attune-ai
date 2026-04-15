---
type: troubleshooting
feature: fix-test
depth: troubleshooting
generated_at: 2026-04-14T14:57:17.002317+00:00
source_hash: add950818a88e621df7bd12cd03ded18fe60e40bac9a1bae6eb24fe1ff69abc8
status: generated
---

# Troubleshoot fix-test

## Before you start

The fix-test feature provides automated test execution, coverage tracking, and lifecycle management. When tests fail unexpectedly or the system doesn't respond correctly to file changes, use this guide to diagnose and fix the issues.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Tests not running automatically | Verify `TestLifecycleManager` initialization and file event handlers in your project |
| Coverage tracking fails | Check that `coverage.xml` exists and is valid XML format at the expected path |
| Stale test warnings persist | Run `get_stale_tests()` to see if the detection logic matches your actual test files |
| Queue processing hangs | Check `get_pending_count()` and verify no tasks are stuck with invalid status values |
| File change events ignored | Confirm the `ProjectIndex` is properly initialized and file paths are relative to project root |

## Step-by-step diagnosis

1. **Reproduce with minimal setup.**
   Create a simple test case that isolates the failing behavior. For test execution issues, try calling `run_tests_with_tracking()` directly with just the required parameters.

2. **Check the task queue status.**
   Run `TestLifecycleManager.get_status()` to see pending tasks and queue health. Look for tasks stuck in 'pending' status or unexpected error states in the results.

3. **Verify file path resolution.**
   Many issues stem from incorrect file paths. Ensure all paths are relative to the project root and that the `ProjectIndex` can find your test files.

4. **Test the core functions individually:**
   - `run_tests_with_tracking()` — Verify test command execution and result capture
   - `track_coverage()` — Confirm coverage.xml parsing (check file exists and has valid XML)
   - `get_file_test_status()` — Test file-to-test mapping logic
   - `TestLifecycleManager.on_file_modified()` — Verify event handling creates appropriate tasks

5. **Enable debug logging.**
   Set logging level to `DEBUG` for the `attune.workflows` modules before running operations. The logs will show task creation, queue processing, and file event handling details.

## Common fixes

- **Missing coverage.xml file:** Run your test suite with coverage first: `python -m pytest --cov=src --cov-report=xml`. The `track_coverage()` function requires this file to exist.

- **Incorrect project root:** Initialize `TestLifecycleManager` and `TestMaintenanceWorkflow` with the absolute path to your project root, not a relative path or subdirectory.

- **Auto-execution disabled:** Set `auto_execute=True` when initializing `TestLifecycleManager` if you want immediate task processing. Without this flag, tasks queue but don't run automatically.

- **Invalid test file patterns:** The system looks for files matching your project's test patterns. If using custom test discovery, ensure your test files are detectable by the `ProjectIndex`.

- **Stale queue file:** If the task queue behaves strangely, clear it with `TestLifecycleManager.clear_queue()` and restart task processing.

- **Git hook integration:** For automatic execution on commits, use `process_git_pre_commit()` and `process_git_post_commit()` with the actual changed file lists from your Git hooks.

## Source files

- `src/attune/workflows/test_runner.py`
- `src/attune/workflows/test_maintenance.py`
- `src/attune/workflows/test_lifecycle.py`

**Tags:** `tests`, `debugging`, `fixes`
