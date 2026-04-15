---
type: task
feature: refactor-plan
depth: task
generated_at: 2026-04-14T14:52:04.001034+00:00
source_hash: 05ca199fb5b9d09ed7030f06c407e71de2e78a2433624c15a7beacf294de4d07
status: generated
---

# Work with refactor plan

Use the refactor plan workflow when you need to identify technical debt and generate a prioritized roadmap for code improvements.

## Prerequisites

- Access to the project source code
- Python environment with the refactor plan module installed

## Run refactor plan analysis

1. **Execute the workflow from the command line:**
   ```bash
   python -m attune.workflows.refactor_plan_report /path/to/your/codebase
   ```

2. **Review the generated report sections:**
   - **Summary**: Tech debt score (0-100) and executive overview
   - **Refactoring**: Prioritized opportunities with effort estimates and risk levels
   - **Suggestions**: Actionable next steps ordered by priority

3. **Verify the analysis completed successfully:**
   The report includes findings from all three subagents: debt-scanner, impact-analyzer, and plan-generator.

## Customize report formatting

1. **Modify the report structure** by editing `format_refactor_plan_report()` in `src/attune/workflows/refactor_plan_report.py`.

2. **Update the analysis prompts** by modifying the `_TASK_PROMPT_TEMPLATE` constant to change how subagents analyze your code.

3. **Test your changes:**
   ```bash
   pytest -k "refactor-plan"
   ```

## Integrate with workflow automation

1. **Use RefactorPlanWorkflow programmatically:**
   ```python
   from attune.workflows.refactor_plan import RefactorPlanWorkflow

   workflow = RefactorPlanWorkflow()
   result = workflow.execute(path="/path/to/codebase")
   ```

2. **Access structured results** from the `WorkflowResult` object for further processing or integration with other tools.

## Key files

- `src/attune/workflows/refactor_plan.py` — Core workflow orchestration
- `src/attune/workflows/refactor_plan_report.py` — Report formatting and CLI interface
