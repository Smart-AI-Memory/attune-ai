# Telemetry

## Quickstart

Read your local usage from Python — the singleton reads the same store
the workflows write to:

```python
from attune.telemetry import UsageTracker

tracker = UsageTracker.get_instance()      # process-wide singleton
stats = tracker.get_stats(days=30)
print(stats["total_calls"], "calls", stats["total_cost"], "USD")
```

Or from a conversation, call the `telemetry_stats` MCP tool, which reads
the same on-disk store (`~/.attune/telemetry/usage.jsonl`).

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

## Reference

The public surface is exported from `attune.telemetry`.

### `UsageTracker` — selected members

| Member | Purpose |
|--------|---------|
| `get_instance(**kwargs) -> UsageTracker` | Process-wide singleton accessor. |
| `track_llm_call(workflow, stage, tier, model, provider, cost, tokens, cache_hit, cache_type, duration_ms, ...)` | Record one LLM call. |
| `get_stats(days=30) -> dict` | Rolled-up usage (`total_calls`, `total_cost`, `by_workflow`, …). |
| `calculate_savings(days=30) -> dict` | Cache/tier savings over the window. |
| `get_recent_entries()` / `get_cache_stats()` / `export_to_dict()` | Read the store back. |
| `flush()` / `reset()` | Force a write / clear the store. |

### `FeedbackLoop` — selected members

| Member | Purpose |
|--------|---------|
| `record_feedback(workflow_name, stage_name, tier, quality_score, metadata=None) -> str` | Record a quality score; returns the entry id. |
| `recommend_tier(workflow_name, stage_name, current_tier=None) -> TierRecommendation` | Recommend a tier for the stage. |
| `get_quality_stats(workflow_name, stage_name, tier=None) -> QualityStats \| None` | Per-stage quality stats; `None` only when no feedback exists for the stage. |
| `get_underperforming_stages()` | Stages below `QUALITY_THRESHOLD` (0.7). |
| `MIN_SAMPLES` / `QUALITY_THRESHOLD` / `FEEDBACK_TTL` | `10` / `0.7` / `604800` s. |

### Other classes

| Class | Purpose |
|-------|---------|
| `TelemetryFeatures` | Feature/Redis availability (`list_all_features`, `is_redis_available`). |
| `HeartbeatCoordinator` | Agent liveness (`beat`, `get_active_agents`, `get_stale_agents`). |
| `EventStreamer` | Event streams (`publish_event`, `consume_events`). |
| `ApprovalGate` | Human-in-the-loop approvals (`ApprovalRequest` / `ApprovalResponse`). |

<!-- attune-generated: source_hash=70af5f419937014536c9522dee18a1346bb18f723c2ed51057c807380c66ee6b feature=telemetry kind=how-to generated_at=2026-06-24 -->
