---
type: comparison
feature: fix-test
depth: comparison
generated_at: 2026-06-22T10:21:37.523920+00:00
source_hash: 26d8af3fe4cef200ee3e0528559c0e39b2bd3756956371d1e78427e02cb6385b
status: generated
---

# TestMaintenanceWorkflow vs manual tracking functions

The fix-test feature offers two approaches for keeping tests in step with source changes. Each targets a different level of automation.

## Feature comparison

| Feature | TestMaintenanceWorkflow | Manual tracking functions |
|---------|------------------------|---------------------------|
| **Automation level** | Workflow orchestration | Manual execution |
| **File change handling** | Event handlers map a change to a `TestPlanItem` | No detection |
| **Planning** | Builds a `TestMaintenancePlan` you can filter and review | No planning |
| **Execution model** | On-demand `run()`; you choose which items to act on | Immediate execution |
| **Configuration complexity** | Low (project root only) | Minimal (optional params) |

## Detailed tradeoffs

**TestMaintenanceWorkflow** gives you structured control. You trigger it with `run()` (or per-file via `on_file_created/modified/deleted`), and it returns a `TestMaintenancePlan` of `TestPlanItem` entries — each with an `action`, `priority`, and `auto_executable` flag. You can review planned work before acting and run only the safe subset via `get_auto_executable_items()`. Best when you want visibility into what will happen before it does.

**Manual tracking functions** give you precise control over individual operations with zero setup cost. Each function (`run_tests_with_tracking`, `track_coverage`, `get_file_test_status`, …) executes immediately and returns specific results. Fastest for one-off debugging, but you coordinate the work yourself.

## Use TestMaintenanceWorkflow when...

- You want changes mapped to prioritized test work automatically
- You want to review planned actions before execution
- You need structured reporting via `TestMaintenancePlan` objects
- You want to auto-run the safe items and defer `REVIEW`/`MANUAL` ones

## Use manual tracking functions when...

- You're debugging specific test failures interactively
- You need to integrate test tracking into existing scripts or tools
- You want immediate results for a specific file or suite
- You're working with a small number of files

**Rule of thumb:** reach for `TestMaintenanceWorkflow` when you want a reviewable plan across many files; drop to the tracking functions for targeted, one-off operations.

## Source files

- `src/attune/workflows/test_runner.py`
- `src/attune/workflows/test_maintenance.py`

**Tags:** `tests`, `debugging`, `fixes`
