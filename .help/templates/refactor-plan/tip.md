---
type: tip
feature: refactor-plan
depth: tip
generated_at: 2026-04-14T14:53:23.160648+00:00
source_hash: 05ca199fb5b9d09ed7030f06c407e71de2e78a2433624c15a7beacf294de4d07
status: generated
---

# Tip: working effectively with refactor plan

## Start with the workflow, not the report formatting

Use `RefactorPlanWorkflow.execute()` to generate plans, then pass the result to `format_refactor_plan_report()` for display. The workflow orchestrates three specialized subagents (debt-scanner, impact-analyzer, plan-generator) that each contribute domain expertise to the final roadmap.

The workflow produces structured data that the formatter converts to readable reports — treating them as separate concerns keeps your code cleaner when you need custom output formats.

## Why this matters

The refactor planner's strength comes from combining multiple analysis perspectives into a single prioritized roadmap. Bypassing the workflow means losing the debt scoring, impact analysis, and risk assessment that make the recommendations actionable.

## Source files

- `src/attune/workflows/refactor_plan.py`
- `src/attune/workflows/refactor_plan_report.py`

**Tags:** `refactor`, `tech-debt`, `complexity`
