---
type: task
feature: deep-review
depth: task
generated_at: 2026-05-04T02:28:25.316934+00:00
source_hash: e32648187b67c25e74699fc7a341857694ff7edd49f5c3d2fd4b545c1bdf65e4
status: generated
---

# Run deep review

Run deep review when you need comprehensive code analysis across security, quality, and test coverage dimensions.

## Prerequisites

- Access to the target codebase
- Claude Agent SDK configured in your environment
- Permission to read the files you want to review

## Execute a deep review

1. **Import the workflow class.**
   ```python
   from attune.workflows.deep_review import DeepReviewAgentSDKWorkflow
   ```

2. **Initialize the workflow.**
   ```python
   workflow = DeepReviewAgentSDKWorkflow()
   ```

3. **Run the review on your target path.**
   ```python
   result = workflow.execute(path="/path/to/your/code")
   ```

4. **Access the consolidated report.**
   The result contains findings from three specialized reviewers:
   - Security vulnerabilities and risks
   - Code quality issues and maintainability concerns
   - Test coverage gaps and missing test scenarios

## Verify the review completed

Check that your `WorkflowResult` contains:
- Overall health score (0-100)
- Findings categorized by severity
- Actionable recommendations ranked by impact
- Specific file paths and line numbers for each finding

The review runs three passes automatically — you don't need to coordinate the security-reviewer, quality-reviewer, and test-gap-reviewer subagents manually.
