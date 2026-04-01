---
type: error
name: costreport-is-a-dataclass-not-a-dict
confidence: Verified
tags: [python]
source: .claude/CLAUDE.md
---

# Error: `CostReport` is a dataclass, not a dict

## Signature

AttributeError: 'CostReport' object has no attribute 'get'

## Root Cause

The `WorkflowBatchRunner._execute_one()` method used `result.cost_report.get("total_cost", cost)` which fails with `AttributeError: 'CostReport' object has no attribute 'get'`.

## Resolution

1. use `getattr(result.cost_report, "total_cost", cost)`
2. Always check whether a result attribute is a dataclass or dict before choosing `.get()` vs `getattr()`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `CostReport` is a dataclass, not a dict
