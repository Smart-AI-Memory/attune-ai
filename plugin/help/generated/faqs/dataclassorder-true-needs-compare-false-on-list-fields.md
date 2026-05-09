---
type: faq
name: dataclassorder-true-needs-compare-false-on-list-fields
tags: [python]
source: .claude/CLAUDE.md
---

# FAQ: Why do I get `TypeError` (dataclass(order=True) needs compare=False on list fields)?

## Answer

Adding `order=True` to a dataclass enables `sorted()` but fails with `TypeError` if any field contains a `list` (unhashable for comparison). This fixed `GenerationResult` in `help/generator.py` which was unsortable.

**How to fix:**
- Use `field(default_factory=list, compare=False)` on list fields to exclude them

```
order=True
```

## Related Topics
- **Error**: Detailed error: `dataclass(order=True)` needs `compare=False` on list
  fields
