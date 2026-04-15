---
type: error
feature: deep-review
depth: error
generated_at: 2026-04-14T14:54:15.383219+00:00
source_hash: 97ad56b1e61d7e30b29c330d79cfa3d58efe35f1fa3640447d3cbf304737b484
status: generated
---

# Deep Review errors

Failures in the multi-pass code review workflow that coordinates three specialized subagents for security, quality, and test gap analysis.

## Common error signatures

- `WorkflowExecutionError` - Subagent coordination failures during review passes
- `AgentSDKError` - Claude Agent SDK communication issues with security-reviewer, quality-reviewer, or test-gap-reviewer subagents
- `ValueError` - Invalid codebase path or malformed review parameters
- `TimeoutError` - Review workflow exceeds execution limits when processing large codebases
- `FileNotFoundError` - Target codebase path does not exist or is inaccessible

## Where errors originate

Errors typically occur in the `DeepReviewAgentSDKWorkflow.execute()` method when:

- Subagent initialization fails for one of the three reviewers (security, quality, test gaps)
- Codebase analysis hits resource limits or permission issues
- Report synthesis encounters malformed findings from individual subagents
- Path resolution fails for the target review directory

Check `src/attune/workflows/deep_review.py` for the specific failure point.

## How to diagnose

1. **Verify the codebase path exists and is readable.** The workflow requires access to analyze files at the specified path. Permission errors often manifest as `OSError` or `FileNotFoundError`.

2. **Check subagent availability.** If you see `AgentSDKError`, one of the three specialized subagents (security-reviewer, quality-reviewer, test-gap-reviewer) may be unavailable or misconfigured.

3. **Monitor workflow execution time.** Large codebases can trigger timeout errors. Review the scope of files being analyzed and consider breaking large reviews into smaller chunks.

4. **Examine subagent output format.** If synthesis fails, individual subagents may be returning findings in unexpected formats. Check that each reviewer produces structured output compatible with the consolidation step.

## Source files

- `src/attune/workflows/deep_review.py`

**Tags:** `review`, `security`, `quality`, `tests`
