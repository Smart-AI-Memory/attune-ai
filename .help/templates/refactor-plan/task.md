---
type: task
feature: refactor-plan
depth: task
generated_at: 2026-05-04T02:27:56.841732+00:00
source_hash: 048ea0ef75e8eaeda7382792e46947bba2ddef4a450bb9395be4c8ba0c1d1f38
status: generated
---

# Work with refactor plan

Use refactor plan when you need to modify how the refactoring analysis workflow processes code or formats its output.

## Prerequisites

- Access to the project source code
- Understanding of the RefactorPlanWorkflow class and its subagents

## Locate the component to modify

The refactor plan feature has two main components:

- **Core workflow**: `RefactorPlanWorkflow` in `src/attune/workflows/refactor_plan.py` — orchestrates the three subagents (debt-scanner, impact-analyzer, plan-generator)
- **Output formatting**: `format_refactor_plan_report()` in `src/attune/workflows/refactor_plan_report.py` — converts analysis results into readable reports

## Modify the workflow logic

1. **Edit the RefactorPlanWorkflow class** to change how subagents coordinate:
   - Update `_SUBAGENT_NAMES` to add or remove specialized analyzers
   - Modify `_SYSTEM_PROMPT` to change the orchestrator's behavior
   - Edit `_TASK_PROMPT_TEMPLATE` to adjust the analysis structure

2. **Test your workflow changes** by running the CLI:
   ```bash
   python -m attune.workflows.refactor_plan_report <path>
   ```

## Modify the report format

1. **Edit `format_refactor_plan_report()`** to change output structure:
   - Adjust section headers, priority ordering, or effort estimates
   - Add new analysis categories or metrics
   - Change how file paths and line numbers display

2. **Verify the formatting** by checking the generated markdown structure matches your intended layout.

## Test your changes

Run the refactor plan workflow on a sample codebase to verify:
- Subagents execute correctly and produce expected findings
- Report formatting displays all analysis results clearly
- Priority ordering and effort estimates make sense

You'll know the task worked when the refactor plan produces a structured report with actionable refactoring recommendations prioritized by impact and effort.
