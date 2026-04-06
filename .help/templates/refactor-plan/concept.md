---
feature: refactor-plan
depth: concept
generated_at: 2026-04-06T04:29:09.010547+00:00
source_hash: 05ca199fb5b9d09ed7030f06c407e71de2e78a2433624c15a7beacf294de4d07
status: generated
---

# Refactor Plan

## How it works

Detect code smells and generate a prioritized refactoring roadmap.

The main building blocks are:

- **`RefactorPlanWorkflow`** — Prioritizes technical debt using Agent SDK subagents to analyze code quality and suggest improvements.

Under the hood, this feature spans 2 source
files covering:

- Refactor planning workflow execution
- Report formatting and command-line interface

## What connects to it

This feature relates to: refactor, tech-debt, complexity.

Other parts of the codebase interact with
refactor plan through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `RefactorPlanWorkflow` | Prioritizes technical debt using Agent SDK subagents to analyze code quality and suggest improvements. | `src/attune/workflows/refactor_plan.py` |
