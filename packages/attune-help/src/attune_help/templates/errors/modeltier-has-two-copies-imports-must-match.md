---
type: error
name: modeltier-has-two-copies-imports-must-match
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Error: `ModelTier` has two copies — imports must match

## Signature

`ModelTier` has two copies — imports must match

## Root Cause

The enum `ModelTier` exists in both `attune.models` and `attune.workflows.base` as separate classes (`id()` differs). Tests comparing `tier_map` values will fail if the import source doesn't match the workflow's import. Check which module the workflow imports from and use the same one in tests.

## Resolution

1. Check which module the workflow imports from and use the same one in tests

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `ModelTier` has two copies — imports must match
- Task: Update test mocks and assertions
