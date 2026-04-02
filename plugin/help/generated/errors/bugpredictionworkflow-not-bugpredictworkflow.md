---
type: error
name: bugpredictionworkflow-not-bugpredictworkflow
confidence: Verified
tags: [imports, claude-code]
source: .claude/CLAUDE.md
---

# Error: `BugPredictionWorkflow` not `BugPredictWorkflow`

## Signature

ImportError

## Root Cause

The class in `attune.workflows.bug_predict` is `BugPredictionWorkflow`. The MCP server had `BugPredictWorkflow` which caused `ImportError`. Always verify the actual class name with `grep` before writing an import.

## Resolution

1. Always verify the actual class name with `grep` before writing an import

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `BugPredictionWorkflow` not `BugPredictWorkflow`
