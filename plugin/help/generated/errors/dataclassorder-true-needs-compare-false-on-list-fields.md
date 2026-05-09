---
type: error
name: dataclassorder-true-needs-compare-false-on-list-fields
confidence: Verified
tags: [python]
source: .claude/CLAUDE.md
---

# Error: `dataclass(order=True)` needs `compare=False` on list
  fields

## Signature

TypeError

## Root Cause

Adding `order=True` to a dataclass enables `sorted()` but fails with `TypeError` if any field contains a `list` (unhashable for comparison). Use `field(default_factory=list, compare=False)` on list fields to exclude them. This fixed `GenerationResult` in `help/generator.py` which was unsortable.

## Resolution

1. Adding `order=True` to a dataclass enables `sorted()` but fails with `TypeError` if any field contains a `list` (unhashable for comparison)
2. Use `field(default_factory=list, compare=False)` on list fields to exclude them

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `dataclass(order=True)` needs `compare=False` on list
  fields
