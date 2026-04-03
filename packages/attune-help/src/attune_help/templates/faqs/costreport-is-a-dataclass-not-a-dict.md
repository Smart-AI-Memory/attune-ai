---
type: faq
name: costreport-is-a-dataclass-not-a-dict
tags: [python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about costReport is a dataclass, not a dict?

## Answer

The `WorkflowBatchRunner._execute_one()` method used `result.cost_report.get("total_cost", cost)` which fails with `AttributeError: 'CostReport' object has no attribute 'get'`.

**How to fix:**
- use `getattr(result.cost_report, "total_cost", cost)`
- Always check whether a result attribute is a dataclass or dict before choosing `.get()` vs `getattr()`

```
WorkflowBatchRunner._execute_one()
```

## Related Topics
- **Error**: Detailed error: `CostReport` is a dataclass, not a dict
