---
type: concept
feature: fix-test
depth: concept
generated_at: 2026-04-14T14:55:50.759331+00:00
source_hash: add950818a88e621df7bd12cd03ded18fe60e40bac9a1bae6eb24fe1ff69abc8
status: generated
---

# Fix Test

## How it works

Fix-test automates test lifecycle management by tracking source code changes and generating maintenance plans for keeping tests current and healthy.

The system operates through event-driven workflows that respond to file changes in your project. When you create, modify, or delete source files, `TestLifecycleManager` automatically queues appropriate test actions — like creating tests for new files, updating tests for modified code, or cleaning up orphaned tests. These actions get packaged into structured maintenance plans that you can execute immediately or schedule for later.

## Core components

**Test planning structures** organize maintenance work into actionable items:

- `TestPlanItem` represents a single maintenance task with its file path, required action (create, update, delete), priority level, and estimated effort
- `TestMaintenancePlan` collects these items into a complete project-wide plan with filtering methods to find tasks by action type or priority
- `TestAction` and `TestPriority` enums standardize the available actions and their urgency levels

**Workflow orchestration** handles the automation:

- `TestLifecycleManager` serves as the central event handler, listening for file system changes and converting them into queued test tasks
- `TestMaintenanceWorkflow` executes the actual maintenance work, with methods to identify files needing tests and detect stale test files
- `TestTask` represents queued work items with scheduling and status tracking

## Execution and monitoring

The system includes tracking utilities for Tier 1 automation. `run_tests_with_tracking()` executes test suites while recording results, `track_coverage()` processes coverage.xml files to monitor test effectiveness, and `track_file_tests()` maintains test status for individual source files.

You can integrate fix-test into Git workflows through pre-commit and post-commit hooks, schedule regular maintenance runs, or trigger it manually when needed. The queue system lets you batch operations and filter by priority to handle urgent issues first.
