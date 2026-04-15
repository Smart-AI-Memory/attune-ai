---
type: faq
feature: refactor-plan
depth: faq
generated_at: 2026-04-14T14:53:06.322153+00:00
source_hash: 05ca199fb5b9d09ed7030f06c407e71de2e78a2433624c15a7beacf294de4d07
status: generated
---

# Refactor Plan FAQ

## What is refactor plan?

A workflow that detects code smells and generates a prioritized refactoring roadmap using three specialized subagents: debt-scanner, impact-analyzer, and plan-generator.

## When should I use refactor plan?

Use refactor plan when you need to assess technical debt in your codebase and create an actionable refactoring strategy. It's particularly useful for large codebases where you want to prioritize which refactoring efforts will have the most impact.

## How do I run a refactor plan analysis?

You can run it through the CLI using `main()` or programmatically with `RefactorPlanWorkflow`. The workflow analyzes your codebase and produces a structured report with tech debt scores, prioritized refactoring opportunities, and actionable next steps.

## What does the output look like?

The refactor plan generates a human-readable report with three sections:
- **Summary**: Overall tech debt score (0-100) and executive summary
- **Refactoring**: Prioritized opportunities with effort estimates and risk levels
- **Suggestions**: Actionable next steps ordered by priority

## How do I format the results for presentation?

Use `format_refactor_plan_report()` to convert the raw workflow output into a readable report format. This function takes the result dictionary and input data, then returns a formatted string.

## How do I debug refactor plan issues?

Run `pytest -k "refactor-plan" -v` first to check if the tests pass. If your code still fails, add `logger.debug` statements at suspected failure points and re-run with logging enabled to trace the workflow execution.

## Where are the source files?

- `src/attune/workflows/refactor_plan.py`
- `src/attune/workflows/refactor_plan_report.py`

**Tags:** `refactor`, `tech-debt`, `complexity`
