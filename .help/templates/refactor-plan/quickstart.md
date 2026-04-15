---
type: quickstart
feature: refactor-plan
depth: quickstart
generated_at: 2026-04-14T14:53:14.342327+00:00
source_hash: 05ca199fb5b9d09ed7030f06c407e71de2e78a2433624c15a7beacf294de4d07
status: generated
---

# Quickstart: refactor plan

Run the refactor planning workflow to analyze your codebase and generate a prioritized tech debt roadmap:

```python
from attune.workflows.refactor_plan import RefactorPlanWorkflow

workflow = RefactorPlanWorkflow()
result = workflow.execute(path="/path/to/your/codebase")
print(result)
```

## Run the analysis

1. **Execute the workflow** on your target codebase:
   ```python
   workflow = RefactorPlanWorkflow()
   result = workflow.execute(path="/path/to/your/project")
   ```

2. **Format the output** into a readable report:
   ```python
   from attune.workflows.refactor_plan_report import format_refactor_plan_report

   report = format_refactor_plan_report(result.data, {"path": "/path/to/your/project"})
   print(report)
   ```

3. **Review the structured output** which includes:
   - Overall tech debt score (0-100)
   - Prioritized refactoring opportunities with effort and risk estimates
   - Actionable next steps ordered by priority

Expected output format:
```
## Summary
Tech debt score: 65/100
The codebase shows moderate technical debt with several refactoring opportunities...

## Refactoring
1. Extract method in user_service.py:45-78 (effort: medium, risk: low)
2. Reduce cyclomatic complexity in data_processor.py:12-89 (effort: large, risk: medium)
...

## Suggestions
1. Start with quick wins in utility functions
2. Plan larger refactoring for core business logic
...
```

**Next:** Run the CLI version with `python -m attune.workflows.refactor_plan_report` to analyze a project directory directly from the command line.
