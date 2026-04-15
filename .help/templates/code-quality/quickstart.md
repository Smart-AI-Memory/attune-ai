---
type: quickstart
feature: code-quality
depth: quickstart
generated_at: 2026-04-14T14:41:40.807796+00:00
source_hash: b7e7be04c17fbc5cdc5e0ffa118eb0ba70c9043509d9f75f395c0c87cf29bbe5
status: generated
---

# Quickstart: code quality

```python
from attune.workflows.code_review import CodeReviewWorkflow

workflow = CodeReviewWorkflow()
result = workflow.execute(path="/path/to/your/codebase")
print(result.content)
```

This runs four specialized reviewers (security, quality, performance, and architecture) against your codebase and returns a unified report with findings and actionable suggestions.

## Run a code review

1. **Import and create the workflow:**
   ```python
   from attune.workflows.code_review import CodeReviewWorkflow
   workflow = CodeReviewWorkflow()
   ```

2. **Execute the review on your codebase:**
   ```python
   result = workflow.execute(path="/path/to/your/project")
   ```

3. **View the structured report:**
   ```python
   print(result.content)
   ```

## Expected output

You'll see a markdown report with sections for Summary (including a 0-100 health score), Security, Quality, Performance, Architecture, and prioritized Suggestions. Each section contains findings with specific file paths and line numbers when applicable.

## Next steps

Read the code-quality concept guide to understand how the four specialized subagents work together and how to customize their behavior.
