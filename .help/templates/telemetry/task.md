---
type: task
name: telemetry-task
feature: telemetry
depth: task
generated_at: 2026-06-24T00:53:03.849694+00:00
source_hash: 70af5f419937014536c9522dee18a1346bb18f723c2ed51057c807380c66ee6b
status: generated
---

# Usage tracking, model-tier feedback loops, and agent-coordination signals

## Tasks

### See your usage and cost stats

**Goal:** roll up recent LLM usage without a dashboard.

**Steps:**

```python
from attune.telemetry import UsageTracker

stats = UsageTracker.get_instance().get_stats(days=30)
print(stats["total_calls"], stats["total_cost"])
print(stats["cache_hit_rate"], "cache hit rate")
print(stats["by_workflow"])
```

**Verify:** `get_stats(days=30)` returns a dict with `total_calls`,
`total_cost`, `total_tokens_input`/`total_tokens_output`,
`cache_hits`/`cache_misses`/`cache_hit_rate`, and the `by_workflow`,
`by_tier`, `by_provider` breakdowns.

### Estimate cost savings

**Goal:** see what caching and tier routing saved.

**Steps:**

```python
from attune.telemetry import UsageTracker

savings = UsageTracker.get_instance().calculate_savings(days=30)
print(savings)
```

**Verify:** `calculate_savings(days=30)` returns a dict summarizing the
savings over the window.

### Record feedback and get a tier recommendation

**Goal:** let the feedback loop pick the cheapest sufficient tier.

**Steps:**

```python
from attune.telemetry import FeedbackLoop

loop = FeedbackLoop()
# tier strings are lowercase: "cheap" / "capable" / "premium"
loop.record_feedback(
    "code-review", "security", tier="capable", quality_score=0.92
)
rec = loop.recommend_tier("code-review", "security", current_tier="capable")
print(rec.recommended_tier, rec.reason)
```

**Verify:** `record_feedback(...)` returns the entry id (a `str`);
`recommend_tier(...)` returns a `TierRecommendation`. Tier strings are
**lowercase** — `recommend_tier` only looks up `cheap`/`capable`/
`premium`, so feedback recorded under another casing is invisible to it.
The `MIN_SAMPLES` (10) gate lives in `recommend_tier`: until the stage's
tier has 10 samples it keeps the current tier (reason `"Insufficient
data …"`); with no matching feedback at all it reports `"No feedback
data available"`.
