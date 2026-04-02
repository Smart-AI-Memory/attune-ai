---
type: warning
name: replacing-a-mixin-based-class-scatters-test-failures-across
confidence: Verified
tags: [testing, git]
source: .claude/CLAUDE.md
---

# Warning: Replacing a mixin-based class scatters test failures across many
  files

## Condition

When merging `CodeReviewWorkflow` from 5 mixins into an SDK-native class, tests for old internal methods (`_classify`, `_scan`, `_gather_project_context`, `should_skip_stage`) were spread across 6+ test files (unit, workflow, integration, coverage batches)

## Risk

Grep for ALL method names being removed across the entire test tree before considering the migration done — `pytest -k "code_review"` catches failures that file-specific runs miss

## Mitigation

1. When merging `CodeReviewWorkflow` from 5 mixins into an SDK-native class, tests for old internal methods (`_classify`, `_scan`, `_gather_project_context`, `should_skip_stage`) were spread across 6+ test files (unit, workflow, integration, coverage batches)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Replacing a mixin-based class scatters test failures across many
  files
