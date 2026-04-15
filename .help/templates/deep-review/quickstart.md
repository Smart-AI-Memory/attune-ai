---
type: quickstart
feature: deep-review
depth: quickstart
generated_at: 2026-04-14T14:55:11.283650+00:00
source_hash: 97ad56b1e61d7e30b29c330d79cfa3d58efe35f1fa3640447d3cbf304737b484
status: generated
---

# Quickstart: deep review

Run a comprehensive code review analyzing security, quality, and test coverage.

```python
from src.attune.workflows.deep_review import DeepReviewAgentSDKWorkflow

workflow = DeepReviewAgentSDKWorkflow()
result = workflow.execute(path="/path/to/your/codebase")
print(result.consolidated_report)
```

## Run your first review

1. **Create the workflow instance**
   ```python
   from src.attune.workflows.deep_review import DeepReviewAgentSDKWorkflow
   workflow = DeepReviewAgentSDKWorkflow()
   ```

2. **Execute the review** on your target codebase
   ```python
   result = workflow.execute(path="/path/to/your/project")
   ```

3. **View the consolidated report**
   ```python
   print(result.consolidated_report)
   ```

## Expected output

The workflow produces a structured report with five sections:

- **Summary**: Overall health score (0-100) and finding counts
- **Security**: Vulnerability findings ordered by severity
- **Quality**: Code quality issues ordered by severity
- **Test Gaps**: Missing test coverage ordered by priority
- **Suggestions**: Top 5-10 actionable improvements with specific references

Each finding includes file paths and line numbers for easy navigation.

## Next steps

Configure custom review criteria by exploring the workflow's subagent parameters in the reference documentation.
