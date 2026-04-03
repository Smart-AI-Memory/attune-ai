---
type: warning
name: non-baseworkflow-classes-in-workflow-registry-crash-the-cli
confidence: Verified
tags: [imports, git]
source: .claude/CLAUDE.md
---

# Warning: Non-BaseWorkflow classes in workflow registry crash the CLI

## Condition

Classes registered in `_DEFAULT_WORKFLOW_NAMES` that don't inherit BaseWorkflow (missing `execute()`, `run_stage()`, or wrong method signatures) will crash `attune workflow run`

## Risk

Classes registered in `_DEFAULT_WORKFLOW_NAMES` that don't inherit BaseWorkflow (missing `execute()`, `run_stage()`, or wrong method signatures) will crash `attune workflow run`

## Mitigation

1. Classes registered in `_DEFAULT_WORKFLOW_NAMES` that don't inherit BaseWorkflow (missing `execute()`, `run_stage()`, or wrong method signatures) will crash `attune workflow run`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Non-BaseWorkflow classes in workflow registry crash the CLI
