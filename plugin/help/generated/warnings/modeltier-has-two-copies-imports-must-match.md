---
type: warning
name: modeltier-has-two-copies-imports-must-match
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Warning: `ModelTier` has two copies — imports must match

## Condition

The enum `ModelTier` exists in both `attune.models` and `attune.workflows.base` as separate classes (`id()` differs)

## Risk

Tests comparing `tier_map` values will fail if the import source doesn't match the workflow's import

## Mitigation

1. Check which module the workflow imports from and use the same one in tests

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `ModelTier` has two copies — imports must match
