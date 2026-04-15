---
type: error
feature: code-quality
depth: error
generated_at: 2026-04-14T14:40:51.637975+00:00
source_hash: b7e7be04c17fbc5cdc5e0ffa118eb0ba70c9043509d9f75f395c0c87cf29bbe5
status: generated
---

# Code Quality errors

Failures in the CodeReviewWorkflow when analyzing codebases for security, quality, performance, and architectural issues.

## Common error signatures

- `FileNotFoundError`: Path specified in workflow execution doesn't exist
- `PermissionError`: Insufficient permissions to read target codebase files
- `ValueError`: Invalid workflow configuration or malformed subagent responses
- `TimeoutError`: Subagent execution exceeds configured limits
- `KeyError`: Missing required fields in subagent output structure

## Where errors originate

Errors typically occur during workflow execution when the CodeReviewWorkflow coordinates its four specialized subagents:

- `CodeReviewWorkflow.execute()` in `src/attune/workflows/code_review.py` — Main orchestration method that manages security-reviewer, quality-reviewer, perf-reviewer, and architect-reviewer subagents

## How to diagnose

1. **Verify the target path exists and is readable.** The workflow requires access to the codebase directory specified in the `path` parameter. Check file permissions and that the path points to a valid code repository.

2. **Examine subagent coordination failures.** If one of the four specialized subagents (security, quality, performance, architecture) fails to produce expected output, the workflow cannot synthesize the final report. Look for incomplete or malformed responses from individual reviewers.

3. **Check the structured output format.** The workflow expects each subagent to return findings as structured markdown. Parsing failures occur when subagent responses don't match the expected format with Summary, Security, Quality, Performance, Architecture, and Suggestions sections.

4. **Validate workflow initialization.** Ensure the CodeReviewWorkflow is properly configured with access to all four subagent types defined in `_SUBAGENT_NAMES`.

## Source files

- `src/attune/workflows/code_review.py`

**Tags:** `review`, `quality`, `bugs`
