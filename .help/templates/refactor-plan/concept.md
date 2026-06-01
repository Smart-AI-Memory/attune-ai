---
feature: refactor-plan
depth: concept
generated_at: 2026-06-01T11:47:06.465837+00:00
source_hash: 6f279448091cd9ecd115ce65a7c82e22149b5ff442f0841471de09a630a0f293
status: generated
---

# Refactor Plan

## How it works

Detect code smells and generate a prioritized refactoring roadmap.

The main building blocks are:

- **`RefactorPlanWorkflow`** — Prioritize tech debt with Agent SDK subagents.

Under the hood, this feature spans 2 source
files covering:

- Refactor Plan Report Formatting and CLI

## What connects to it

This feature relates to: refactor, tech-debt, complexity.

Other parts of the codebase interact with
refactor plan through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `RefactorPlanWorkflow` | Prioritize tech debt with Agent SDK subagents. | `src/attune/workflows/refactor_plan.py` |
