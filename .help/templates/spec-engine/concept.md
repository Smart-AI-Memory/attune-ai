---
feature: spec-engine
depth: concept
generated_at: 2026-04-06T04:35:43.403443+00:00
source_hash: 9a5e04c503c29d581c2787038d961b7e425b0163cece10376e6b23a94fbb5aa4
status: generated
---

# Spec Engine

## How it works

The spec engine enables spec-driven development by executing XML specifications with human approval loops and persistent state management.

The main building blocks are:

- **`SpecState`** — Tracks execution progress and task completion status for resumable spec runs.
- **`TaskResult`** — Captures the outcome and quality gate status of individual pipeline tasks.
- **`PipelineResult`** — Aggregates results across all tasks in a complete pipeline execution.
- **`PipelineOrchestrator`** — Executes XML spec tasks sequentially with built-in quality gates and approval checkpoints.

Under the hood, this feature spans 16 source
files covering:

- Human-readable task formatting with progress indicators and detailed status reports.
- Interactive spec execution with per-task approval gates and quality validation.
- Persistent state storage in HTML comments within plan files for resumable workflows.

## What connects to it

This feature relates to: spec, planning.

Other parts of the codebase interact with
spec engine through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `SpecState` | Tracks execution progress and task completion status for resumable spec runs. | `src/attune/spec/state.py` |
| `TaskResult` | Captures the outcome and quality gate status of individual pipeline tasks. | `src/attune/pipeline/models.py` |
| `PipelineResult` | Aggregates results across all tasks in a complete pipeline execution. | `src/attune/pipeline/models.py` |
| `PipelineOrchestrator` | Executes XML spec tasks sequentially with built-in quality gates and approval checkpoints. | `src/attune/pipeline/orchestrator.py` |
