---
type: task
name: refactor-plan-task
feature: refactor-plan
depth: task
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: a8b5dc570639e8d2770577c7a57611f86fbf596d547e3e6299cd6a5dd1281ea0
status: generated
---

# Work with Refactor Plan

Use the refactor plan workflow when you want to scan a codebase for technical debt and produce a prioritized refactoring roadmap with effort estimates and risk levels.

## Prerequisites

- Access to the project source code
- The relevant source files:
  - `src/attune/workflows/refactor_plan.py`
  - `src/attune/workflows/refactor_plan_report.py`

## Run a refactor plan

1. **Instantiate `RefactorPlanWorkflow`.**
   Import the class from `workflows.refactor_plan` and create an instance. The constructor accepts keyword arguments that are forwarded to the underlying subagents (`debt-scanner`, `impact-analyzer`, and `plan-generator`).

   ```python
   from workflows.refactor_plan import RefactorPlanWorkflow

   workflow = RefactorPlanWorkflow()
   ```

2. **Call `execute()` with the target path.**
   Pass the path you want to analyze as a keyword argument. The workflow coordinates all three subagents and returns a `WorkflowResult`.

   ```python
   result = workflow.execute(path="src/auth/")
   ```

3. **Format the output.**
   Pass the result and your original input data to `format_refactor_plan_report()` to produce a human-readable report.

   ```python
   from workflows.refactor_plan_report import format_refactor_plan_report

   report = format_refactor_plan_report(result, input_data={"path": "src/auth/"})
   print(report)
   ```

4. **Or run the CLI entry point directly.**
   Call `main()` from `workflows.refactor_plan_report` to run the full workflow from the command line without writing any Python.

## Modify report formatting

1. **Open `src/attune/workflows/refactor_plan_report.py`.**
   The `format_refactor_plan_report(result: dict, input_data: dict) -> str` function is the single place responsible for converting raw workflow output into the final report string.

2. **Identify the section to change.**
   The report is structured around three sections driven by the workflow output: **Summary**, **Refactoring**, and **Suggestions**. Find the block that renders the section you need to adjust.

3. **Edit the formatting logic and verify the signature.**
   `format_refactor_plan_report` takes `result` (the `dict` returned by `execute()`) and `input_data` (the original inputs). Make sure your changes consume only fields present in those arguments.

4. **Confirm the output looks correct.**
   Call `format_refactor_plan_report` directly in a Python shell with a representative `result` dict and inspect the returned string.

## Verify success

Run the test suite targeting this feature:

```
pytest -k "refactor-plan"
```

All tests pass and `format_refactor_plan_report` returns a non-empty string that includes a **Summary**, **Refactoring**, and **Suggestions** section for a valid `result` input.
