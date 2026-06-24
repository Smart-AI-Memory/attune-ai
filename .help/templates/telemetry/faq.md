---
type: faq
name: telemetry-faq
feature: telemetry
depth: faq
status: manual
---

# Telemetry FAQ

## What does attune telemetry record?

Three things, all exported from `attune.telemetry`: every LLM call's
cost, tokens, cache hits, and duration (`UsageTracker`); a quality score
per workflow stage and tier (`FeedbackLoop`); and agent-coordination
signals — heartbeats, event streams, and approval requests
(`HeartbeatCoordinator`, `EventStreamer`, `ApprovalGate`).

## Where is telemetry data stored by default?

Locally, under `~/.attune/telemetry` (the usage ledger is
`usage.jsonl`); the directory is overridable via `ATTUNE_HOME`. Nothing
leaves your machine unless you explicitly enable an opt-in phone-home.
The Redis-backed coordination signals use Redis keys/streams instead of
the local file.

## How do I see my usage and cost metrics?

From Python, `UsageTracker.get_instance().get_stats(days=30)` (and
`calculate_savings(days=30)`); from a conversation, the
`telemetry_stats` MCP tool; or the ops dashboard — all read the same
on-disk store.

## Why won't the feedback loop change my recommended tier?

`recommend_tier` needs at least `MIN_SAMPLES` (10) feedback samples for
the stage's tier before it moves; below that it keeps the current tier
with reason "Insufficient data". Tier strings are lowercase
(`cheap`/`capable`/`premium`) — feedback recorded under another casing
is invisible to `recommend_tier`.

## Does `get_quality_stats` need 10 samples too?

No. `get_quality_stats` returns `None` only when there is no feedback
for the stage at all; with any samples it returns a `QualityStats`
(its `sample_count` tells you how many). The `MIN_SAMPLES` gate lives in
`recommend_tier`, not here.

## How do I check whether an agent is still running?

With the coordination classes (Redis-backed):
`HeartbeatCoordinator.is_agent_alive(...)`, `get_active_agents()`, and
`get_stale_agents()`; `EventStreamer.consume_events()` /
`get_recent_events()` read the event stream. Guard their use behind
`TelemetryFeatures.is_redis_available()`.

## Where are the source files?

All telemetry source lives under `src/attune/telemetry/`.

**Tags:** `telemetry`, `metrics`
