---
type: error
name: costreport-fields-are-named-not-positional
confidence: Verified
tags: [git, python]
source: .claude/CLAUDE.md
---

# Error: `CostReport` fields are named, not positional

## Signature

TypeError

## Root Cause

The `CostReport` dataclass requires `total_cost`, `baseline_cost`, `savings`, `savings_percent`, and `by_stage`. Using `total_input_tokens` or `total_output_tokens` raises `TypeError` — those fields don't exist. Always check the dataclass definition in `data_classes.py` before constructing.

## Resolution

1. Always check the dataclass definition in `data_classes.py` before constructing

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: `CostReport` fields are named, not positional
- Tip: Best practice: `CostReport` fields are named, not positional
