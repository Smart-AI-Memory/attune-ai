---
type: tip
feature: models
depth: tip
generated_at: 2026-04-14T15:15:33.214280+00:00
source_hash: de302041f650efb4293949074bddd09934c2b7bde5a2f12db73f81a599c75353
status: generated
---

# Use AdaptiveModelRouter for intelligent model selection

## Recommendation

Use `AdaptiveModelRouter` instead of hardcoding model choices in your workflows. It selects models based on historical performance data, cost constraints, and latency requirements.

```python
router = AdaptiveModelRouter(telemetry)
model = router.get_best_model("code_review", "analysis", max_cost=0.05)
```

## Why this matters

The router learns from real usage patterns and automatically routes tasks to models that perform best for your specific workflows, reducing both costs and failures compared to static model assignment.

## The tradeoff

You need telemetry data for the router to make good decisions — it starts with reasonable defaults but improves over time as it collects performance metrics from actual usage.
