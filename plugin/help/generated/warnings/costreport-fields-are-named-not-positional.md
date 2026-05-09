---
type: warning
name: costreport-fields-are-named-not-positional
confidence: Verified
tags: [git, python]
source: .claude/CLAUDE.md
---

# Warning: `CostReport` fields are named, not positional

## Condition

The `CostReport` dataclass requires `total_cost`, `baseline_cost`, `savings`, `savings_percent`, and `by_stage`

## Risk

Using `total_input_tokens` or `total_output_tokens` raises `TypeError` — those fields don't exist

## Mitigation

1. Always check the dataclass definition in `data_classes.py` before constructing

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `CostReport` fields are named, not positional
