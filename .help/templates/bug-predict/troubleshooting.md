---
type: troubleshooting
feature: bug-predict
depth: troubleshooting
generated_at: 2026-04-14T14:48:17.311159+00:00
source_hash: bdce26567d10cd4bcfc419ff9a7191f2baac8f5a8e219c06d9ae6c6e38f95653
status: generated
---

# Troubleshoot bug predict

## Before you start

The bug predict feature analyzes your codebase to identify potential bug locations using pattern detection and risk correlation. It runs three specialized subagents (pattern-scanner, risk-correlator, prevention-advisor) that produce a unified prediction report.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `BugPredictionWorkflow` raises an exception | Verify the codebase path exists and is readable |
| Empty or missing prediction report | Check if `format_bug_predict_report()` received valid result data |
| CLI command fails to start | Confirm you're calling `main()` with a valid codebase path argument |
| Report shows "no patterns found" | Verify your code contains detectable complexity patterns (nested loops, long functions, etc.) |
| Subagent timeout or hang | Check if the target codebase is extremely large (>10k files) or contains binary files |

## Step-by-step diagnosis

1. **Test with a minimal codebase.**
   Create a small Python file with obvious bug patterns (nested loops, long functions) and run bug predict against it. If this works, the issue is specific to your target codebase.

2. **Verify subagent initialization.**
   Check that all three subagents from `_SUBAGENT_NAMES` are available: pattern-scanner, risk-correlator, and prevention-advisor. Missing subagents will cause workflow failures.

3. **Enable debug output.**
   Run the CLI with verbose logging to see the workflow progression through each subagent. Look for which subagent fails or produces empty results.

4. **Check the workflow execution.**
   Inspect `BugPredictionWorkflow.execute()` return values. The result should contain structured data from all three subagents before formatting.

5. **Validate report formatting.**
   If the workflow completes but the report is malformed, test `format_bug_predict_report()` directly with known good result data.

## Common fixes

- **Path resolution issues.** Ensure your codebase path is absolute or correctly relative to your working directory:
  ```bash
  python -m attune.workflows.bug_predict_report /absolute/path/to/code
  ```

- **Large codebase timeout.** For codebases with thousands of files, increase the workflow timeout or filter to specific directories:
  ```python
  workflow = BugPredictionWorkflow(timeout=300)  # 5 minutes
  ```

- **Missing file permissions.** Bug predict needs read access to all analyzed files. Fix with:
  ```bash
  chmod -R +r /path/to/codebase
  ```

- **Binary file interference.** Exclude binary files that confuse pattern detection by filtering the input to only source files (`.py`, `.js`, etc.).

- **Dependency conflicts.** The subagents may require specific versions of analysis libraries. Check that your environment matches the requirements and reinstall if needed.

## Source files

- `src/attune/workflows/bug_predict.py`
- `src/attune/workflows/bug_predict_*.py`

**Tags:** `bugs`, `prediction`, `scanning`
