---
type: error
name: replacing-a-mixin-based-class-scatters-test-failures-across
confidence: Verified
tags: [testing, git]
source: .claude/CLAUDE.md
---

# Error: Replacing a mixin-based class scatters test failures across many
  files

## Signature

Replacing a mixin-based class scatters test failures across many
  files

## Root Cause

When merging `CodeReviewWorkflow` from 5 mixins into an SDK-native class, tests for old internal methods (`_classify`, `_scan`, `_gather_project_context`, `should_skip_stage`) were spread across 6+ test files (unit, workflow, integration, coverage batches). Grep for ALL method names being removed across the entire test tree before considering the migration done — `pytest -k "code_review"` catches failures that file-specific runs miss.

## Resolution

1. Grep for ALL method names being removed across the entire test tree before considering the migration done — `pytest -k "code_review"` catches failures that file-specific runs miss

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
