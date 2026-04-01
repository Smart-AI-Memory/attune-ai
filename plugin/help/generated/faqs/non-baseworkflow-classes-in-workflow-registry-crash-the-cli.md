---
type: faq
name: non-baseworkflow-classes-in-workflow-registry-crash-the-cli
tags: [imports, git]
source: .claude/CLAUDE.md
---

# FAQ: Why does non-BaseWorkflow classes in workflow registry crash the CLI?

## Answer

Classes registered in `_DEFAULT_WORKFLOW_NAMES` that don't inherit BaseWorkflow (missing `execute()`, `run_stage()`, or wrong method signatures) will crash `attune workflow run`. Only register true BaseWorkflow subclasses; keep standalone utilities importable but out of the registry.

```
_DEFAULT_WORKFLOW_NAMES
```

## Related Topics
- **Error**: Detailed error: Non-BaseWorkflow classes in workflow registry crash the CLI
