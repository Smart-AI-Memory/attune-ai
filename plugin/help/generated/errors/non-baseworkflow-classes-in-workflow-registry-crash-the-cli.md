---
type: error
name: non-baseworkflow-classes-in-workflow-registry-crash-the-cli
confidence: Verified
tags: [imports, git]
source: .claude/CLAUDE.md
---

# Error: Non-BaseWorkflow classes in workflow registry crash the CLI

## Signature

Non-BaseWorkflow classes in workflow registry crash the CLI

## Root Cause

Classes registered in `_DEFAULT_WORKFLOW_NAMES` that don't inherit BaseWorkflow (missing `execute()`, `run_stage()`, or wrong method signatures) will crash `attune workflow run`. Only register true BaseWorkflow subclasses; keep standalone utilities importable but out of the registry.

## Resolution

1. Classes registered in `_DEFAULT_WORKFLOW_NAMES` that don't inherit BaseWorkflow (missing `execute()`, `run_stage()`, or wrong method signatures) will crash `attune workflow run`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Non-BaseWorkflow classes in workflow registry crash the CLI
