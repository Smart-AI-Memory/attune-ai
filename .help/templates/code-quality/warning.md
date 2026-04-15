---
type: warning
feature: code-quality
depth: warning
generated_at: 2026-04-14T14:41:02.358476+00:00
source_hash: b7e7be04c17fbc5cdc5e0ffa118eb0ba70c9043509d9f75f395c0c87cf29bbe5
status: generated
---

# Code Quality cautions

## What to watch for

The `CodeReviewWorkflow` orchestrates four specialized subagents that analyze different aspects of your codebase. While this provides comprehensive coverage, the distributed nature of the workflow creates specific risks you should understand.

## Risk areas

**Subagent dependency failures can corrupt the final report.** The workflow relies on all four subagents (`security-reviewer`, `quality-reviewer`, `perf-reviewer`, `architect-reviewer`) completing successfully before synthesis. If one subagent fails or times out, you may receive an incomplete report that appears valid but misses entire categories of issues.

**Large codebases may exceed context limits during synthesis.** The workflow attempts to synthesize findings from all four subagents into a single unified report. With extensive codebases, the combined output from all subagents may exceed token limits, causing truncated or malformed final reports.

**File path resolution can fail with non-standard project structures.** The workflow expects standard file paths when citing findings. Projects with symbolic links, mounted volumes, or non-standard directory structures may produce reports with broken file references, making it difficult to locate the actual issues.

## How to avoid problems

1. **Monitor subagent completion status.** Check the `WorkflowResult` for any failed subagents before trusting the synthesis. If a subagent fails, re-run the workflow or manually invoke the missing reviewer.

2. **Split large codebases into reviewable chunks.** If your codebase has more than 50,000 lines, consider reviewing modules or directories separately rather than the entire repository at once.

3. **Verify file paths in reports.** After receiving a review, spot-check a few cited file paths to ensure they resolve correctly in your environment. This is especially important in containerized or CI environments.

4. **Test the workflow on a known codebase first.** Before using it on critical code, run `CodeReviewWorkflow` against a small, well-understood codebase to verify it produces accurate findings in your environment.

## Source files

- `src/attune/workflows/code_review.py`

**Tags:** `review`, `quality`, `bugs`
