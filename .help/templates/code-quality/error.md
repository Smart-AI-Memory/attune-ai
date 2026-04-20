---
type: error
feature: code-quality
depth: error
generated_at: 2026-04-19T18:45:54.256615+00:00
source_hash: 44a3613be3cabe60572ba20a4d4a482a2b2727856106c44e43c6eafd7e2cc42e
status: generated
---

# Code Quality errors

Code quality failures occur when the review workflow can't analyze your code or when the specialized subagents encounter problems during execution.

## Common error signatures

- `FileNotFoundError: [Errno 2] No such file or directory` — The specified path doesn't exist or isn't accessible
- `PermissionError: [Errno 13] Permission denied` — Can't read the target files or directory
- `WorkflowExecutionError` — One or more subagents (security-reviewer, quality-reviewer, perf-reviewer, architect-reviewer) failed to complete
- `ValueError: Invalid path format` — The path argument is malformed or points to an unsupported file type
- `TimeoutError` — Review took longer than expected, often on large codebases

## Where errors originate

Errors typically start in the `CodeReviewWorkflow` class when:

- **Path validation fails** — The `execute()` method can't locate or access your specified files
- **Subagent coordination breaks** — One of the four specialized reviewers (security, quality, performance, architecture) encounters an error and can't complete its analysis
- **Result synthesis fails** — The workflow can't merge findings from all subagents into a unified report

Check the `CodeReviewWorkflow.execute()` method first, as it orchestrates the entire review process.

## How to diagnose

1. **Verify your path exists and is readable.** Run `ls -la <your-path>` to confirm the files exist and you have read permissions. Code quality needs to traverse the directory structure and read source files.

2. **Check for unsupported file types.** If your directory contains binary files, large data files, or non-source code, the subagents may fail. Try reviewing a smaller, source-code-only subset first.

3. **Look for subagent-specific failures.** The error message often indicates which reviewer failed — security-reviewer, quality-reviewer, perf-reviewer, or architect-reviewer. This narrows down whether it's a parsing issue, analysis complexity, or resource constraint.

4. **Test with a minimal case.** If reviewing a large codebase fails, try a single file first: `/code-quality src/config.py`. If that works, gradually increase scope to isolate where the failure occurs.

5. **Check available memory and disk space.** Deep reviews of large codebases can be resource-intensive. The workflow may fail if system resources are exhausted during analysis.

## Source files

- `src/attune/workflows/code_review.py`

**Tags:** `review`, `quality`, `bugs`
