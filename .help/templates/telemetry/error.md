---
type: error
name: telemetry-error
feature: telemetry
depth: error
generated_at: 2026-06-24T00:53:03.849694+00:00
source_hash: 70af5f419937014536c9522dee18a1346bb18f723c2ed51057c807380c66ee6b
status: generated
---

# Usage tracking, model-tier feedback loops, and agent-coordination signals

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `get_stats` totals are 0 | No calls recorded yet, or buffered and unflushed | Run a workflow, or call `flush()` | low |
| `recommend_tier` keeps returning the current tier | Fewer than `MIN_SAMPLES` (10) feedback rows for the stage's tier | Record more feedback before expecting a switch | medium |
| `recommend_tier` says "No feedback data available" despite recorded feedback | Tier recorded with non-lowercase casing (e.g. `"CAPABLE"`); it only matches `cheap`/`capable`/`premium` | Record with lowercase tier strings | medium |
| Coordination calls fail / no agents listed | Redis-backed features unavailable | Check `TelemetryFeatures.is_redis_available()`; install the Redis extra | medium |
| Stats look stale | Entries older than retention/TTL aged out | `retention_days` (90) bounds the store; feedback `FEEDBACK_TTL` is 7 days | low |

### Risk areas

- **Buffered writes.** `UsageTracker` batches; a reader may miss the
  newest calls until `flush()` or the buffer fills (`buffer_size`).
- **`MIN_SAMPLES` gate.** Tier recommendations are conservative by
  design — they need 10 samples before they move.
- **Redis-gated coordination.** `EventStreamer` /
  `HeartbeatCoordinator` need Redis; guard with `TelemetryFeatures`.

### Diagnosis order

1. `UsageTracker.get_instance().get_stats(days=1)` — is anything
   recorded?
2. `flush()` then re-read, to rule out buffering.
3. For tier recommendations, `get_quality_stats(...)` returns `None`
   only when the stage has no feedback; `recommend_tier` needs
   `MIN_SAMPLES` (and lowercase tier strings) before it moves.
4. For coordination, `TelemetryFeatures().is_redis_available()`.
