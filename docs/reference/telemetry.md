# Telemetry

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

<!-- attune-generated: source_hash=70af5f419937014536c9522dee18a1346bb18f723c2ed51057c807380c66ee6b feature=telemetry kind=reference generated_at=2026-06-24 -->
