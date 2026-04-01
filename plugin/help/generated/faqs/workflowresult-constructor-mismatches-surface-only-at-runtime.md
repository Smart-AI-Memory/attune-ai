---
type: faq
name: workflowresult-constructor-mismatches-surface-only-at-runtime
tags: [testing, git, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about workflowResult constructor mismatches surface only at runtime?

## Answer

`ParallelTestGenerationWorkflow.execute()` was passing non-existent kwargs (`workflow_name`, `stages_executed`). Fixed in `c67ad740` — now passes all required fields (`success`, `stages`, `started_at`, `completed_at`, `total_duration_ms`).

```
ParallelTestGenerationWorkflow.execute()
```

## Related Topics
- **Error**: Detailed error: `WorkflowResult` constructor mismatches surface only at
  runtime
