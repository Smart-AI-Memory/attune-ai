---
type: troubleshooting
feature: code-quality
depth: troubleshooting
generated_at: 2026-04-14T14:41:15.695069+00:00
source_hash: b7e7be04c17fbc5cdc5e0ffa118eb0ba70c9043509d9f75f395c0c87cf29bbe5
status: generated
---

# Troubleshoot code quality

## Before you start

The code quality feature uses `CodeReviewWorkflow` to orchestrate four specialized subagents (security, quality, performance, and architecture reviewers) that analyze your codebase and generate a unified review report.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `CodeReviewWorkflow` raises an exception during execution | Python traceback for the exact line in `execute()` method |
| Review report is incomplete or missing sections | Subagent names in `_SUBAGENT_NAMES` and their individual outputs |
| Review never completes or hangs | Subagent execution status and any blocking I/O operations |
| Report format is malformed | Template structure in `_TASK_PROMPT_TEMPLATE` and markdown generation |

## Step-by-step diagnosis

1. **Reproduce with minimal code.**
   Create a test script that instantiates `CodeReviewWorkflow` and calls `execute()` with the same path argument. Run it in isolation to confirm the failure occurs without your application's broader context.

2. **Check the target codebase.**
   Verify the path you're passing to `execute()` exists and contains reviewable code files. Empty directories or non-code files can cause subagents to fail silently.

3. **Enable debug logging for subagent coordination.**
   Set your logging level to `DEBUG` before calling `execute()`. The workflow logs subagent startup, execution, and completion events that reveal which reviewer is failing.

4. **Examine subagent outputs individually.**
   Check if all four subagents in `_SUBAGENT_NAMES` ('security-reviewer', 'quality-reviewer', 'perf-reviewer', 'architect-reviewer') are producing output. A single failing subagent can block the unified report generation.

## Common fixes

- **Invalid codebase path.** Ensure the path passed to `execute()` points to a directory containing source code files. The workflow expects reviewable code, not documentation or configuration files.

- **Missing subagent dependencies.** Each specialized reviewer may require specific analysis tools. Check that your environment includes static analysis libraries, security scanners, or performance profiling tools that the subagents depend on.

- **Insufficient memory for large codebases.** The four parallel subagents can consume significant memory when analyzing large repositories. Monitor memory usage and consider reviewing smaller code sections if you encounter out-of-memory errors.

- **Timeout on slow analysis.** Complex codebases may exceed default timeout limits. If the workflow hangs, check for configurable timeout parameters in the `execute()` method or consider breaking large reviews into smaller chunks.

## Source files

- `src/attune/workflows/code_review.py` — Main `CodeReviewWorkflow` class with subagent coordination

**Tags:** `review`, `quality`, `bugs`
