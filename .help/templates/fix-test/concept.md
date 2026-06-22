---
feature: fix-test
depth: concept
generated_at: 2026-06-22T10:21:37.523920+00:00
source_hash: 26d8af3fe4cef200ee3e0528559c0e39b2bd3756956371d1e78427e02cb6385b
status: generated
---

# Fix Test

The fix-test feature keeps a project's tests healthy by reacting to source-file changes, diagnosing what test work each change implies, and producing a prioritized, partly auto-executable maintenance plan.

## How it works

`TestMaintenanceWorkflow` is the central coordinator. It turns file-system events into a `TestMaintenancePlan` — an ordered set of `TestPlanItem` entries, each describing one piece of test work: which file it concerns, what `TestAction` to take, and at what `TestPriority`.

The building blocks:

- **`TestMaintenanceWorkflow`** — coordinates everything. `run(context)` produces a maintenance plan; the event handlers `on_file_created()`, `on_file_modified()`, and `on_file_deleted()` translate a single file change into the test work it implies.
- **`TestPlanItem`** — one unit of test work. Carries `file_path`, `action`, `priority`, `reason`, `test_file_path`, `estimated_effort`, and `auto_executable`.
- **`TestMaintenancePlan`** — the assembled plan. Filter it with `get_items_by_action()`, `get_items_by_priority()`, or `get_auto_executable_items()`.
- **`TestAction`** — what to do with a test: `CREATE`, `UPDATE`, `REVIEW`, `DELETE`, `SKIP`, or `MANUAL`.
- **`TestPriority`** — how urgent: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, or `DEFERRED`.

## How a change becomes a plan

1. A source file changes. The matching handler — `on_file_created()`, `on_file_modified()`, or `on_file_deleted()` — inspects it and decides which `TestAction` applies (a new module needs a `CREATE`; a deleted one may imply a `DELETE` or `REVIEW`).
2. The workflow assigns a `TestPriority` based on impact and rolls the resulting `TestPlanItem` entries into a `TestMaintenancePlan`.
3. Callers act on the plan: `get_auto_executable_items()` returns the items safe to run automatically, while higher-touch items (`REVIEW`, `MANUAL`) are surfaced for a human.

## Tracking what actually ran

The companion module `test_runner.py` records outcomes so the workflow can reason about staleness and gaps:

- `run_tests_with_tracking()` runs a suite and records the result for Tier 1 monitoring.
- `track_coverage()` and `track_file_tests()` persist coverage and per-file test status.
- `get_file_test_status()` and `get_files_needing_tests()` answer "is this file covered?" and "what still needs tests?" — the same signals `TestMaintenanceWorkflow.get_stale_tests()` and `get_test_health_summary()` build on.

## When this matters

You work with fix-test when you want to keep test coverage in step with source changes automatically — surfacing the tests a change demands, prioritizing them by impact, and auto-running the safe ones — rather than discovering gaps after a regression lands.
