---
type: concept
feature: refactor-plan
depth: concept
generated_at: 2026-04-14T14:51:54.985696+00:00
source_hash: 05ca199fb5b9d09ed7030f06c407e71de2e78a2433624c15a7beacf294de4d07
status: generated
---

# Refactor Plan

The refactor plan feature analyzes codebases to identify technical debt and generates prioritized refactoring roadmaps with effort estimates and risk assessments.

## Core orchestration

The `RefactorPlanWorkflow` coordinates three specialized subagents—debt-scanner, impact-analyzer, and plan-generator—to examine different aspects of code quality. Each subagent focuses on its domain expertise, then the workflow synthesizes their findings into a unified refactoring strategy.

The orchestrator follows a structured system prompt that positions it as a "senior refactoring plan orchestrator" responsible for producing thorough but concise analysis with specific file paths and line numbers.

## Report structure

The generated refactoring report contains three standardized sections:

- **Summary**: An overall tech debt score (0-100) with a brief executive overview of refactoring opportunities
- **Refactoring**: Prioritized opportunities with effort estimates (small/medium/large) and risk levels (low/medium/high)
- **Suggestions**: Actionable next steps ordered by priority, distinguishing between quick wins and longer-term improvements

The `format_refactor_plan_report` function transforms the raw analysis results into human-readable markdown following this structure.

## Command-line interface

You can run refactor planning directly through the `main()` entry point, which provides a CLI wrapper around the workflow execution. This allows you to analyze any codebase path and receive the formatted refactoring report as output.
