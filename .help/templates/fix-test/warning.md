---
type: warning
feature: fix-test
depth: warning
generated_at: 2026-06-22T10:21:37.523920+00:00
source_hash: 26d8af3fe4cef200ee3e0528559c0e39b2bd3756956371d1e78427e02cb6385b
status: generated
---

# Fix Test cautions

## What to watch for

Test maintenance turns file changes into test work — review what it plans before you act on it.

## Risk areas

### Auto-executable items still modify your codebase

`TestMaintenancePlan.get_auto_executable_items()` returns the items the workflow considers safe to run without review — but running them can still create, update, or delete test files. Inspect `plan.items` and confirm each `action` before executing, especially `DELETE`.

### Coverage tracking requires specific file formats

The `track_coverage()` function expects a valid `coverage.xml` file in the correct format. If your coverage tool generates a different format or the file is corrupted, tracking will fail with a `ValueError`. Always verify your coverage configuration produces compatible XML before enabling tracking.

### Event handlers fire for any file path you pass

`on_file_created()`, `on_file_modified()`, and `on_file_deleted()` act on whatever path they're given — including non-source files. If you wire them to a broad file watcher, filter to meaningful source changes first so the plan doesn't fill with irrelevant items.

### A plan is only as good as the action mapping

Each `TestPlanItem` gets its `TestAction` and `TestPriority` from the workflow's mapping logic. If items come back with the wrong action, review the `on_file_*` handlers rather than acting on the bad items.

### Stale test detection depends on file timestamps

The system identifies stale tests by comparing modification times between source files and their corresponding test files. If your build system or version control modifies timestamps unexpectedly, you may get false positives. Verify timestamp accuracy before trusting `get_stale_tests()` reports.

## How to avoid problems

1. **Review before executing.** Call `run()` and read `plan.items` first. Filter with `get_auto_executable_items()` and leave `REVIEW`/`MANUAL` items for a human.

2. **Filter the paths you feed in.** When driving the event handlers from a watcher, exclude build artifacts, temporary files, and vendor directories.

3. **Check priorities.** Use `get_items_by_priority(TestPriority.CRITICAL)` to focus on the highest-impact work first instead of running everything at once.

4. **Validate coverage setup early.** Test your coverage configuration with `track_coverage()` on a known-good coverage file before integrating it into automated workflows.

## Source files

- `src/attune/workflows/test_runner.py`
- `src/attune/workflows/test_maintenance.py`

**Tags:** `tests`, `debugging`, `fixes`
