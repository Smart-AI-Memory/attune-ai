---
type: concept
feature: spec-engine
depth: concept
generated_at: 2026-05-04T02:38:56.324868+00:00
source_hash: dfb05ee79541939dac0529f016b44e21b04ef77d58372da1d6d5b857d97ef4d0
status: generated
---

# Spec Engine

The spec engine orchestrates task execution from XML plans with quality gates and approval loops, transforming spec-driven development from planning to working code.

## Core components

The spec engine is built around four key classes:

**`PipelineOrchestrator`** — Executes XML task plans with quality gates after each step. You give it a spec file path and optional flags to skip gates, tests, or simplification. It runs tasks sequentially, checking quality at each stage.

**`TaskResult`** — Captures what happened when a single task ran. This includes whether the task executed, passed its quality gate and tests, plus error details, cost, and a severity classification based on gate scores.

**`PipelineResult`** — Aggregates results from a complete run. It tracks all task results, total cost, duration, and provides a success property that only returns true when every task executed and passed its gates.

**`SpecState`** — Tracks execution progress for resumable runs. It knows which tasks completed, what's currently running, whether auto-run is enabled, and when state last changed. This data persists as HTML comments in plan files.

## Execution flow

The engine reads XML task blocks from plan files using `read_spec()`, then presents them to you as markdown tables showing task names, acceptance criteria, and completion status. When you approve execution, the orchestrator runs each task in sequence.

After each task completes, the engine runs quality gates that score the implementation and determine severity levels. You can approve the result, ask for a redo with new instructions, or continue auto-running remaining tasks if quality passes.

The engine saves execution state between runs, so you can resume interrupted work or review progress across sessions. State tracking includes completion status, current position, and auto-run preferences.

## Quality gates and approval

Every task execution includes quality assessment unless you skip gates. The engine scores implementation quality and classifies results by severity through the `TaskResult.severity` property. Failed gates require your explicit approval before proceeding.

The approval system prevents runaway execution — nothing runs without your consent. You can execute with per-task approval using `execute_with_approval()`, which calls back after each task completes and waits for your decision.

## State persistence

The engine maintains execution state in the plan files themselves as HTML comments, making progress visible in version control. You can load existing state with `load_state()`, save updates with `save_state()`, or clear all progress with `clear_state()`.

This design means spec execution is resumable by default — if a run stops partway through, the next execution picks up where it left off based on the saved state.
