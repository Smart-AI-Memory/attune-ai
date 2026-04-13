---
feature: refactor-plan
depth: concept
generated_at: 2026-04-13T16:55:48.433943+00:00
source_hash: 05ca199fb5b9d09ed7030f06c407e71de2e78a2433624c15a7beacf294de4d07
status: generated
---

# Refactor Plan

## How it works

Detect code smells and generate a prioritized refactoring roadmap.

The main building blocks are:

- **`RefactorPlanWorkflow`** — Prioritizes technical debt using Agent SDK subagents to analyze code quality and complexity.

Under the hood, this feature spans 2 source
files covering:

- Refactor Planning Workflow
- Refactor Plan Report Formatting and CLI

## What connects to it

This feature relates to: refactor, tech-debt, complexity.

Other parts of the codebase interact with
refactor plan through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `RefactorPlanWorkflow` | Prioritizes technical debt using Agent SDK subagents to analyze code quality and complexity. | `src/attune/workflows/refactor_plan.py` |
