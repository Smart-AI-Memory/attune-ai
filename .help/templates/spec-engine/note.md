---
type: note
feature: spec-engine
depth: note
generated_at: 2026-04-14T15:26:30.380721+00:00
source_hash: da2776f0fd9a91d42dcf9bea5dec82a4fb9b85009623c3ae56e9db9136c29d2e
status: generated
---

# Note: spec engine

## Context

The spec engine enables spec-driven development by executing XML specification files as pipelines with human approval loops and quality gates.

## Core workflow

The spec engine follows a three-phase workflow:

1. **State management** — Track execution progress across pipeline runs using `SpecState`, which persists completed tasks and current position in HTML comments within plan files
2. **Task presentation** — Display tasks in human-readable formats through presenter functions that generate markdown tables and detailed views
3. **Pipeline execution** — Run tasks through `PipelineOrchestrator` with configurable quality gates, test validation, and approval checkpoints

## Key components

**State tracking:**
- `SpecState` maintains execution progress with completed task lists and auto-run flags
- State persists in plan files as HTML comments, allowing resume after interruption
- `load_state()`, `save_state()`, and `clear_state()` manage persistence

**Task execution:**
- `PipelineOrchestrator` executes XML specs with optional quality gates, tests, and simplification
- `TaskResult` captures individual task outcomes including gate scores and error details
- `PipelineResult` aggregates results across all tasks with cost tracking and success status

**Human interaction:**
- `present_tasks()` renders task lists as markdown tables with progress indicators
- `present_task_detail()` shows full task specifications for review
- `execute_with_approval()` enables per-task approval workflows

The engine supports resumable execution — you can stop a pipeline mid-run and resume from the last completed task using `find_resumable_plans()`.

## Source files

- `src/attune/spec/**` — State management and presentation
- `src/attune/pipeline/**` — Orchestration and result models

**Tags:** `spec`, `planning`
