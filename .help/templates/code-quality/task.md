---
type: task
feature: code-quality
depth: task
generated_at: 2026-04-14T14:40:39.429767+00:00
source_hash: b7e7be04c17fbc5cdc5e0ffa118eb0ba70c9043509d9f75f395c0c87cf29bbe5
status: generated
---

# Run a code quality review

Run a code quality review when you need comprehensive analysis of your codebase across security, quality, performance, and architecture dimensions.

## Prerequisites

- Access to the codebase you want to review
- Python environment with the SDK installed

## Execute the review

1. **Import the workflow class.**
   ```python
   from attune.workflows.code_review import CodeReviewWorkflow
   ```

2. **Initialize the workflow.**
   ```python
   workflow = CodeReviewWorkflow()
   ```

3. **Run the review on your target path.**
   ```python
   result = workflow.execute(path="/path/to/your/codebase")
   ```

4. **Access the structured report.**
   The workflow returns a `WorkflowResult` containing markdown with these sections:
   - Summary with overall health score (0-100)
   - Security findings
   - Quality findings
   - Performance findings
   - Architecture findings
   - Prioritized suggestions

## Verify the review worked

Check that your result contains:
- A health score between 0-100 in the Summary section
- Specific file paths and line numbers in the findings
- Actionable suggestions ranked by priority

The review coordinates four specialized subagents (security-reviewer, quality-reviewer, perf-reviewer, architect-reviewer) to provide comprehensive coverage of code quality concerns.
