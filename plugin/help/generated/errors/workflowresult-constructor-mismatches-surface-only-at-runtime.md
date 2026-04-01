---
type: error
name: workflowresult-constructor-mismatches-surface-only-at-runtime
confidence: Verified
tags: [testing, git, python]
source: .claude/CLAUDE.md
---

# Error: `WorkflowResult` constructor mismatches surface only at
  runtime

## Signature

`WorkflowResult` constructor mismatches surface only at
  runtime

## Root Cause

`ParallelTestGenerationWorkflow.execute()` was passing non-existent kwargs (`workflow_name`, `stages_executed`). Fixed in `c67ad740` — now passes all required fields (`success`, `stages`, `started_at`, `completed_at`, `total_duration_ms`). Lesson: always exercise `execute()` end-to-end in tests to catch dataclass mismatches that lint can't see.

## Resolution

1. `ParallelTestGenerationWorkflow.execute()` was passing non-existent kwargs (`workflow_name`, `stages_executed`)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `WorkflowResult` constructor mismatches surface only at
  runtime
- Task: Update test mocks and assertions
