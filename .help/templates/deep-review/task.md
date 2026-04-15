---
type: task
feature: deep-review
depth: task
generated_at: 2026-04-14T14:54:02.539359+00:00
source_hash: 97ad56b1e61d7e30b29c330d79cfa3d58efe35f1fa3640447d3cbf304737b484
status: generated
---

# Run a deep code review

Run a deep code review when you need comprehensive analysis across security, code quality, and test coverage for a codebase.

## Prerequisites

- Access to the codebase you want to review
- Claude Agent SDK configured and available
- Python environment with the workflow dependencies installed

## Execute the review

1. **Import the workflow class.**
   ```python
   from src.attune.workflows.deep_review import DeepReviewAgentSDKWorkflow
   ```

2. **Initialize the workflow.**
   ```python
   reviewer = DeepReviewAgentSDKWorkflow()
   ```

3. **Run the review on your target codebase.**
   ```python
   result = reviewer.execute(path="/path/to/your/codebase")
   ```

4. **Access the consolidated report.**
   The workflow returns a `WorkflowResult` containing the synthesized findings from all three specialized reviewers (security, quality, and test gaps).

## Verify the review completed

Check that the result contains all expected sections:
- Summary with overall health score (0-100)
- Security findings ordered by severity
- Quality findings ordered by severity
- Test gaps ordered by priority
- Top 5-10 actionable suggestions with impact rankings

The review leverages three specialized subagents that analyze your code independently, then consolidates their findings into a single comprehensive report with specific file paths and line numbers for each issue.
