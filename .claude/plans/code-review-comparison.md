# Code Review Workflow Comparison

**Date:** 2026-03-08 23:03:12
**Path:** `src/attune/workflows/`

## Execution Time

| Workflow | Time (ms) | Status |
|----------|-----------|--------|
| CodeReviewWorkflow (mixin) | 33,508 | FAILED: Workflow execution error (data/config): Stage classify faile |
| AgentCodeReviewWorkflow (SDK) | 114 | FAILED: Agent SDK error: ProcessError: Command failed with exit code |

**Faster:** AgentCodeReviewWorkflow (SDK) (by 33,394 ms)

## Stages Executed

| Workflow | Total Stages | Skipped | Executed |
|----------|-------------|---------|----------|
| CodeReviewWorkflow (mixin) | 0 | 0 | 0 |
| AgentCodeReviewWorkflow (SDK) | 1 | 0 | 1 |

## Summaries

### CodeReviewWorkflow (mixin)

(no summary)

### AgentCodeReviewWorkflow (SDK)

(no summary)

## Findings by Category

No structured findings detected in either workflow output.

## Verdict

- **Speed:** New workflow was faster (114 ms vs 33,508 ms)
- **Reliability:** Both workflows failed
