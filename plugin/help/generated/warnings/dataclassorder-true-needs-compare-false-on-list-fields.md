---
type: warning
name: dataclassorder-true-needs-compare-false-on-list-fields
confidence: Verified
tags: [python]
source: .claude/CLAUDE.md
---

# Warning: `dataclass(order=True)` needs `compare=False` on list
  fields

## Condition

Adding `order=True` to a dataclass enables `sorted()` but fails with `TypeError` if any field contains a `list` (unhashable for comparison)

## Risk

Adding `order=True` to a dataclass enables `sorted()` but fails with `TypeError` if any field contains a `list` (unhashable for comparison)

## Mitigation

1. Adding `order=True` to a dataclass enables `sorted()` but fails with `TypeError` if any field contains a `list` (unhashable for comparison)
2. Use `field(default_factory=list, compare=False)` on list fields to exclude them

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `dataclass(order=True)` needs `compare=False` on list
  fields
