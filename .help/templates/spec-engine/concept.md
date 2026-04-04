---
feature: spec-engine
depth: concept
generated_at: 2026-04-04T02:25:50.655254+00:00
source_hash: 9a5e04c503c29d581c2787038d961b7e425b0163cece10376e6b23a94fbb5aa4
status: generated
---

# Spec Engine

## What

Spec-driven development with approval loops

## Why

This feature provides spec engine functionality for the project.

## How

Key components:

- `SpecState` — Execution state for a spec plan.

- `TaskResult` — Result of executing a single pipeline task.

- `PipelineResult` — Aggregated result from a full pipeline run.

- `PipelineOrchestrator` — Executes tasks from an XML spec with quality gates.
