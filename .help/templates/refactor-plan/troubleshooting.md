---
type: troubleshooting
feature: refactor-plan
depth: troubleshooting
generated_at: 2026-04-14T14:52:47.649295+00:00
source_hash: 05ca199fb5b9d09ed7030f06c407e71de2e78a2433624c15a7beacf294de4d07
status: generated
---

# Troubleshoot refactor plan

## Before you start

The refactor plan feature analyzes your codebase to detect tech debt and generate a prioritized refactoring roadmap using three specialized subagents: debt-scanner, impact-analyzer, and plan-generator.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Unexpected exception | Python's traceback for the exact file and line where the error occurs |
| Empty or malformed report output | Return value from `format_refactor_plan_report()` and the `result` dict it receives |
| Missing subagent results | Whether all three subagents (`debt-scanner`, `impact-analyzer`, `plan-generator`) completed successfully |
| Workflow hangs or times out | Agent SDK subagent communication and any I/O operations on the target codebase path |

## Step-by-step diagnosis

1. **Reproduce the issue with minimal input.**
   Run the refactor plan workflow on a small, known codebase to isolate whether the problem is with the workflow itself or your specific input. Use a simple directory with 2-3 Python files.

2. **Verify the codebase path.**
   Confirm that the path you're analyzing exists and is readable. The workflow needs access to scan files and analyze code structure.

3. **Check subagent execution.**
   The `RefactorPlanWorkflow` coordinates three subagents. If any subagent fails, the entire workflow may produce incomplete results. Look for error messages mentioning `debt-scanner`, `impact-analyzer`, or `plan-generator`.

4. **Examine the workflow result.**
   Inspect what `RefactorPlanWorkflow.execute()` returns. The `WorkflowResult` should contain data from all three subagents that gets passed to `format_refactor_plan_report()`.

5. **Enable debug logging.**
   Set your logging level to `DEBUG` to see detailed subagent communication and workflow state transitions.

## Common fixes

- **Fix path permissions.** Ensure the target codebase directory is readable by the workflow process. Run `ls -la /path/to/codebase` to verify permissions.

- **Update Agent SDK dependencies.** The subagents rely on the Agent SDK. If you see import errors or subagent communication failures, run `pip install --upgrade agent-sdk`.

- **Validate codebase structure.** The workflow expects Python code to analyze. If you're pointing it at an empty directory or non-Python files, it may return empty results without clear errors.

- **Clear workflow state.** If the workflow worked previously but now hangs, restart your Python process to clear any cached Agent SDK state or stale subagent connections.

- **Check system prompt configuration.** The workflow uses a specific system prompt to coordinate subagents. If you've modified environment variables or configuration that affects prompt loading, restore the default settings.

## Source files

- `src/attune/workflows/refactor_plan.py`
- `src/attune/workflows/refactor_plan_report.py`

**Tags:** `refactor`, `tech-debt`, `complexity`
