---
type: troubleshooting
feature: code-quality
depth: troubleshooting
generated_at: 2026-04-19T18:46:23.112847+00:00
source_hash: 44a3613be3cabe60572ba20a4d4a482a2b2727856106c44e43c6eafd7e2cc42e
status: generated
---

# Troubleshoot code quality

## Before you start

The code quality feature runs four specialized subagents (security, quality, performance, and architecture reviewers) to analyze your code. When issues occur, they typically stem from the orchestration workflow or individual subagent failures.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `/code-quality` command fails with exception | Check the file path exists and you have read permissions |
| Review hangs or takes extremely long | Verify the target directory size — large codebases may exceed reasonable scan limits |
| Empty or incomplete results | Confirm all four subagents (_SUBAGENT_NAMES) are available and responding |
| Score shows as 0 or missing | Look for subagent communication failures in the workflow logs |
| Results missing specific categories | Check which of the four reviewers (security, quality, performance, architecture) failed to report |

## Step-by-step diagnosis

1. **Verify the target path.**
   Confirm the file or directory you're reviewing exists and is readable:
   ```bash
   ls -la /path/to/your/code
   ```
   The CodeReviewWorkflow needs read access to analyze files.

2. **Test with a minimal example.**
   Try reviewing a single small file first:
   ```
   /code-quality path/to/simple_file.py
   ```
   This isolates whether the issue is with the workflow itself or the complexity of your target.

3. **Check subagent availability.**
   The workflow depends on four specialized reviewers. If any are unavailable, the unified report will be incomplete. Look for error messages mentioning `security-reviewer`, `quality-reviewer`, `perf-reviewer`, or `architect-reviewer`.

4. **Enable debug logging.**
   Set your logging level to DEBUG before running the review to see detailed workflow execution and subagent communication.

5. **Inspect the CodeReviewWorkflow execution.**
   The workflow orchestrates multiple subagents and synthesizes their findings. Check if the failure occurs during:
   - Initial path validation
   - Subagent coordination
   - Result synthesis into the final report

## Common fixes

- **Path issues:** Use absolute paths or verify your current working directory. The workflow needs to locate and read your source files.

- **Permission errors:** Ensure the code quality process has read access to your target files:
  ```bash
  chmod +r /path/to/your/code
  ```

- **Large directory timeouts:** For whole-project scans, start with a subdirectory to confirm the workflow functions, then expand scope gradually.

- **Missing dependencies:** The four specialized subagents may require specific analysis tools. Check that your environment includes all necessary code analysis dependencies.

- **Stale workflow state:** If reviews worked previously but now fail, restart your Claude Code session to clear any cached workflow state.

## Source files

- `src/attune/workflows/code_review.py`

**Tags:** `review`, `quality`, `bugs`
