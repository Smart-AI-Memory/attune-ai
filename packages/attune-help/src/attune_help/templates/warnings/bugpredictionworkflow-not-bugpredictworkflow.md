---
type: warning
name: bugpredictionworkflow-not-bugpredictworkflow
confidence: Verified
tags: [imports, claude-code]
source: .claude/CLAUDE.md
---

# Warning: `BugPredictionWorkflow` not `BugPredictWorkflow`

## Condition

The class in `attune.workflows.bug_predict` is `BugPredictionWorkflow`

## Risk

The class in `attune.workflows.bug_predict` is `BugPredictionWorkflow`

## Mitigation

1. Always verify the actual class name with `grep` before writing an import

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `BugPredictionWorkflow` not `BugPredictWorkflow`
