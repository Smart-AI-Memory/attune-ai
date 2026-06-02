---
type: note
name: refactor-plan-note
feature: refactor-plan
depth: note
generated_at: 2026-06-02T10:56:02.707953+00:00
source_hash: 048ea0ef75e8eaeda7382792e46947bba2ddef4a450bb9395be4c8ba0c1d1f38
status: generated
---

# Note: Refactor Plan

The refactor-plan feature is implemented across two modules with distinct responsibilities.

`workflows.refactor_plan` contains `RefactorPlanWorkflow`, which orchestrates three specialized subagents — `debt-scanner`, `impact-analyzer`, and `plan-generator` — using the Agent SDK. Each subagent focuses on a separate domain; the workflow synthesizes their output into a unified roadmap covering a summary, prioritized refactoring opportunities, and actionable next steps.

`workflows.refactor_plan_report` handles output formatting and CLI access. `format_refactor_plan_report(result, input_data)` converts the raw workflow result into a human-readable report. `main()` is the CLI entry point that runs the full planning workflow from the command line.

The two modules are complementary but separate: `RefactorPlanWorkflow.execute()` produces the result dict, and `format_refactor_plan_report()` consumes it. Neither module inherits from the other.

## Source files

- `src/attune/workflows/refactor_plan.py`
- `src/attune/workflows/refactor_plan_report.py`

**Tags:** `refactor`, `tech-debt`, `complexity`
