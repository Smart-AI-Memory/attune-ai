---
type: troubleshooting
feature: deep-review
depth: troubleshooting
generated_at: 2026-04-14T14:54:43.568217+00:00
source_hash: 97ad56b1e61d7e30b29c330d79cfa3d58efe35f1fa3640447d3cbf304737b484
status: generated
---

# Troubleshoot deep review

## Before you start

The deep review feature performs multi-pass code analysis using three specialized Claude Agent SDK subagents: security-reviewer, quality-reviewer, and test-gap-reviewer. Each subagent analyzes your codebase independently, then the workflow synthesizes their findings into a consolidated report.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `DeepReviewAgentSDKWorkflow.execute()` throws exception | Python traceback for the exact line in `src/attune/workflows/deep_review.py` |
| Empty or incomplete report sections | Return value from `execute()` - verify all three subagents completed successfully |
| Missing file paths or line numbers in findings | Subagent outputs - check if the codebase path passed to `execute()` is valid and readable |
| Workflow hangs or times out | Agent SDK subagent status - one of the three reviewers may be stuck waiting for API responses |

## Step-by-step diagnosis

1. **Reproduce with minimal input.**
   Create a simple test directory with one source file and call `DeepReviewAgentSDKWorkflow.execute(path="test_dir")`. This isolates the workflow from complex codebases and validates the basic execution path.

2. **Check subagent initialization.**
   Verify all three required subagents (`security-reviewer`, `quality-reviewer`, `test-gap-reviewer`) are properly configured in your Agent SDK setup. The workflow expects these exact names from `_SUBAGENT_NAMES`.

3. **Enable Agent SDK logging.**
   Set your logging level to `DEBUG` and look for Claude Agent SDK communication logs. Failed API calls or malformed responses from individual subagents will appear here before the workflow fails.

4. **Validate the codebase path.**
   Ensure the path argument passed to `execute()` points to a readable directory with source files. The workflow needs file system access to analyze code and generate the file paths referenced in findings.

5. **Test subagents individually.**
   If available in your Agent SDK setup, test each subagent (`security-reviewer`, `quality-reviewer`, `test-gap-reviewer`) independently on a small code sample to isolate which reviewer is failing.

## Common fixes

- **Fix Agent SDK configuration.** Ensure your Claude Agent SDK is properly configured with API credentials and the three required subagents are registered. Run `claude-sdk list-agents` or equivalent to verify availability.

- **Update file permissions.** The workflow needs read access to your codebase. Run `chmod -R +r /path/to/codebase` if you see permission errors in the logs.

- **Increase timeout settings.** Large codebases can take time to analyze. If using a custom Agent SDK timeout, increase it to allow all three subagents to complete their analysis.

- **Verify Claude API limits.** The workflow makes multiple API calls through the Agent SDK. Check your Claude API usage and rate limits if you see authentication or quota errors.

- **Clean temporary state.** If the workflow uses temporary files or caches, clear them with `rm -rf /tmp/deep-review-*` or similar, then retry.

## Source files

- `src/attune/workflows/deep_review.py`

**Tags:** `review`, `security`, `quality`, `tests`
