---
type: note
feature: fix-test
depth: note
generated_at: 2026-06-22T10:21:37.523920+00:00
source_hash: 26d8af3fe4cef200ee3e0528559c0e39b2bd3756956371d1e78427e02cb6385b
status: generated
---

# Note: fix test

## Context

The fix-test feature provides test maintenance through event-driven planning. It tracks test coverage, identifies files needing test attention, and turns source-file changes into prioritized maintenance plans.

## Architecture

The feature combines two complementary modules:

**Test execution tracking** (`test_runner.py`) provides opt-in monitoring functions that record test results and coverage data for Tier 1 automation. Key functions include `run_tests_with_tracking()` for explicit test execution tracking and `track_coverage()` for parsing coverage.xml files.

**Test maintenance planning and event handling** (`test_maintenance.py`) defines both the plan model and the coordinator. `TestMaintenancePlan` contains prioritized `TestPlanItem` instances that specify actions like creating or updating tests, each with metadata like estimated effort and an auto-executable flag. `TestMaintenanceWorkflow` responds to file-system changes through its `on_file_created()`, `on_file_modified()`, and `on_file_deleted()` handlers and assembles the plan via `run()`.

## Integration pattern

The modules work together through shared data types. Test execution functions accept workflow IDs that link results to specific maintenance plans. The event handlers produce `TestPlanItem` entries that reference the same `TestAction` and `TestPriority` enums used throughout the plan. This lets the system map a file change to prioritized test work and surface the auto-executable subset for execution.

## Source files

- `src/attune/workflows/test_runner.py`
- `src/attune/workflows/test_maintenance.py`

**Tags:** `tests`, `debugging`, `fixes`
