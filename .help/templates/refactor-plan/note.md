---
type: note
name: refactor-plan-note
feature: refactor-plan
depth: note
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: a8b5dc570639e8d2770577c7a57611f86fbf596d547e3e6299cd6a5dd1281ea0
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
