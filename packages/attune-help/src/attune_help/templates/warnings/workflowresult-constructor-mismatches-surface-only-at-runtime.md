---
type: warning
name: workflowresult-constructor-mismatches-surface-only-at-runtime
confidence: Verified
tags: [testing, git, python]
source: .claude/CLAUDE.md
---

# Warning: `WorkflowResult` constructor mismatches surface only at
  runtime

## Condition

`ParallelTestGenerationWorkflow.execute()` was passing non-existent kwargs (`workflow_name`, `stages_executed`)

## Risk

Ignoring this guidance may cause: `WorkflowResult` constructor mismatches surface only at
  runtime

## Mitigation

1. `ParallelTestGenerationWorkflow.execute()` was passing non-existent kwargs (`workflow_name`, `stages_executed`)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `WorkflowResult` constructor mismatches surface only at
  runtime
