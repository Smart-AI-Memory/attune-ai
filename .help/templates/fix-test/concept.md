---
type: concept
feature: fix-test
depth: concept
generated_at: 2026-05-04T02:28:39.831715+00:00
source_hash: bff04fe2ad91cb5eb72a0a1c91eccca5bb1b81eba3549bb3ac7e694b3e7a98b8
status: generated
---

# Fix Test

Fix-test automatically manages test lifecycles by responding to code changes and scheduling test maintenance tasks based on file events throughout your project.

## Event-driven test management

When you modify source files, fix-test watches for these changes and queues appropriate test actions:

- **File creation** — Schedules test generation for new modules through `on_file_created()`
- **File modification** — Queues test updates when existing code changes via `on_file_modified()`
- **File deletion** — Removes orphaned tests when source files are deleted using `on_file_deleted()`

The `TestLifecycleManager` acts as the central coordinator, transforming file system events into prioritized `TestTask` items that specify what test action to take and when.

## Task prioritization and execution

Each test task gets assigned a priority level through `TestPriority` (high, medium, low) and an action type via `TestAction` (create, update, delete, validate). The system maintains a persistent queue where you can:

- Process tasks by priority using `get_queue_by_priority()`
- Execute batches of work with `process_queue()` up to a specified limit
- Schedule recurring maintenance through `schedule_maintenance()`

For example, a critical bug fix that breaks existing tests gets high priority, while adding tests for edge cases in stable code gets low priority.

## Git workflow integration

Fix-test hooks into your Git workflow at two key points:

- **Pre-commit** — Validates that staged files have corresponding tests via `process_git_pre_commit()`
- **Post-commit** — Schedules test updates for all changed files through `process_git_post_commit()`

This ensures your test suite stays synchronized with code changes without manual intervention.

## Test maintenance planning

The `TestMaintenanceWorkflow` analyzes your entire project to create comprehensive maintenance plans. It identifies files that need tests through `get_files_needing_tests()`, finds outdated tests via `get_stale_tests()`, and generates a `TestMaintenancePlan` with concrete action items.

Each `TestPlanItem` includes the target file, required action, priority level, effort estimate, and whether the task can be automated — giving you a clear roadmap for improving test coverage and keeping tests current.
