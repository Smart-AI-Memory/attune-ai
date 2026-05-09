---
type: faq
name: costreport-fields-are-named-not-positional
tags: [git, python]
source: .claude/CLAUDE.md
---

# FAQ: Why do I get `TypeError` (costReport fields are named, not positional)?

## Answer

The `CostReport` dataclass requires `total_cost`, `baseline_cost`, `savings`, `savings_percent`, and `by_stage`. Using `total_input_tokens` or `total_output_tokens` raises `TypeError` — those fields don't exist.

**How to fix:**
- Always check the dataclass definition in `data_classes.py` before constructing

```
CostReport
```

## Related Topics
- **Error**: Detailed error: `CostReport` fields are named, not positional
