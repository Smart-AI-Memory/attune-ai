---
feature: spec-engine
depth: concept
generated_at: 2026-04-13T17:02:47.385432+00:00
source_hash: da2776f0fd9a91d42dcf9bea5dec82a4fb9b85009623c3ae56e9db9136c29d2e
status: generated
---

# Spec Engine

## How it works

The spec engine executes XML specifications with human-readable task presentation and approval loops.

The main building blocks are:

- **`SpecState`** — Tracks execution state for resumable spec plans
- **`TaskResult`** — Captures the outcome of a single pipeline task execution
- **`PipelineResult`** — Aggregates results from all tasks in a complete pipeline run
- **`PipelineOrchestrator`** — Executes XML spec tasks with quality gate validation

Under the hood, this feature spans 8 source
files covering:

- Human-readable task formatting with markdown tables and progress bars
- Task execution with per-task approval gates
- Persistent state management in HTML comments within plan files

## What connects to it

This feature relates to: spec, planning.

Other parts of the codebase interact with
spec engine through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `SpecState` | Tracks execution state for resumable spec plans | `src/attune/spec/state.py` |
| `TaskResult` | Captures the outcome of a single pipeline task execution | `src/attune/pipeline/models.py` |
| `PipelineResult` | Aggregates results from all tasks in a complete pipeline run | `src/attune/pipeline/models.py` |
| `PipelineOrchestrator` | Executes XML spec tasks with quality gate validation | `src/attune/pipeline/orchestrator.py` |
