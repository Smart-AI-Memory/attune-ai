---
type: error
name: baseworkflow-uses-class-attributes-not-constructor-params
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: BaseWorkflow uses class attributes, not constructor params

## Signature

TypeError

## Root Cause

The `name`, `description`, `stages`, and `tier_map` fields on BaseWorkflow are CLASS ATTRIBUTES, not `__init__()` parameters. Passing them to `super().__init__()` raises `TypeError`. Define them as class-level assignments on the subclass.

## Resolution

1. Passing them to `super().__init__()` raises `TypeError`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
