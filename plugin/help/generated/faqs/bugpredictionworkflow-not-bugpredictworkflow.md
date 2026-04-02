---
type: faq
name: bugpredictionworkflow-not-bugpredictworkflow
tags: [imports, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: Why do I get `ImportError` (bugPredictionWorkflow not BugPredictWorkflow)?

## Answer

The class in `attune.workflows.bug_predict` is `BugPredictionWorkflow`. The MCP server had `BugPredictWorkflow` which caused `ImportError`.

**How to fix:**
- Always verify the actual class name with `grep` before writing an import

```
attune.workflows.bug_predict
```

## Related Topics
- **Error**: Detailed error: `BugPredictionWorkflow` not `BugPredictWorkflow`
