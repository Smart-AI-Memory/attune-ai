---
type: warning
feature: fix-test
depth: warning
generated_at: 2026-04-14T14:57:01.164017+00:00
source_hash: add950818a88e621df7bd12cd03ded18fe60e40bac9a1bae6eb24fe1ff69abc8
status: generated
---

# Fix Test cautions

## What to watch for

Auto-diagnose and fix failing tests — identifies root causes and applies fixes.

## Risk areas

### Automatic test execution can modify your codebase

The `TestLifecycleManager` with `auto_execute=True` will automatically run test fixes without user confirmation. This can modify test files, create new tests, or delete obsolete ones based on file change events. Set `auto_execute=False` during development to review changes before they're applied.

### Coverage tracking requires specific file formats

The `track_coverage()` function expects a valid `coverage.xml` file in the correct format. If your coverage tool generates a different format or the file is corrupted, tracking will fail with a `ValueError`. Always verify your coverage configuration produces compatible XML before enabling tracking.

### Test lifecycle events fire on every file change

File watchers trigger `on_file_created()`, `on_file_modified()`, and `on_file_deleted()` for any project file change, not just source files. This can flood your test task queue with irrelevant maintenance tasks. Use appropriate file filtering in your project configuration to limit events to meaningful changes.

### Queue processing can overwhelm your system

`process_queue()` with a high `max_tasks` value can spawn many concurrent test processes. Each test task may consume significant CPU and memory. Monitor system resources when processing large queues, especially in CI environments with limited capacity.

### Stale test detection depends on file timestamps

The system identifies stale tests by comparing file modification times between source files and their corresponding test files. If your build system or version control modifies timestamps unexpectedly, you may get false positives for stale tests. Verify timestamp accuracy before trusting stale test reports.

## How to avoid problems

1. **Start with manual execution.** Initialize `TestLifecycleManager` with `auto_execute=False` and review the task queue before enabling automatic processing. Use `get_queue()` to inspect pending tasks.

2. **Configure appropriate file filters.** Set up your project to only monitor relevant file types and directories. Exclude build artifacts, temporary files, and vendor directories from test lifecycle events.

3. **Process queues incrementally.** Use smaller `max_tasks` values (5-10) when processing test queues, especially on shared systems. Monitor `get_pending_count()` to avoid overwhelming your environment.

4. **Validate coverage setup early.** Test your coverage configuration with `track_coverage()` on a known good coverage file before integrating it into automated workflows.

## Source files

- `src/attune/workflows/test_runner.py`
- `src/attune/workflows/test_maintenance.py`
- `src/attune/workflows/test_lifecycle.py`

**Tags:** `tests`, `debugging`, `fixes`
