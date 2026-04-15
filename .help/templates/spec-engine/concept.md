---
type: concept
feature: spec-engine
depth: concept
generated_at: 2026-04-14T15:24:26.801940+00:00
source_hash: da2776f0fd9a91d42dcf9bea5dec82a4fb9b85009623c3ae56e9db9136c29d2e
status: generated
---

# Spec Engine

The spec engine executes development tasks defined in XML specifications while maintaining human oversight through approval loops and quality gates.

## Task execution model

The engine breaks down specifications into individual tasks that run sequentially. Each task passes through quality gates that validate the output before proceeding. You can run tasks automatically or pause for manual approval at each step.

The `PipelineOrchestrator` reads XML specs and executes each `DecomposedTask` while tracking results in a `TaskResult`. Quality gates evaluate whether the task output meets requirements by checking tests, simplified versions, and custom validation criteria. If a gate fails, you can review the results and decide whether to continue.

## Execution state persistence

The engine saves progress directly in your plan files as HTML comments, letting you resume interrupted workflows. The `SpecState` tracks which tasks completed successfully, which task is currently running, and whether auto-execution is enabled.

When you run `find_resumable_plans()`, the engine scans for plan files with incomplete state and shows you where you left off. You can pick up exactly where you stopped without re-running completed tasks.

## Human-readable progress tracking

The presentation layer formats task information for easy review during execution. Functions like `present_tasks()` create markdown tables showing task status, while `format_progress_bar()` gives visual feedback on overall completion.

For each task result, the engine shows you the quality gate score, test results, and any errors that occurred. The `TaskResult.severity` property classifies results as passing, warning, or failing to help you quickly assess what needs attention.

## Core components

- **`SpecState`** — Tracks execution progress with completed task IDs, current task, and auto-run settings
- **`TaskResult`** — Contains execution outcomes including quality gate scores, test results, and error details
- **`PipelineResult`** — Aggregates all task results with total cost, duration, and success status
- **`PipelineOrchestrator`** — Coordinates task execution with configurable quality gates and test running
