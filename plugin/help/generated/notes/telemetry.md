---
name: telemetry
source: content/features/telemetry.md
tags:
- telemetry
- metrics
type: note
---

# Usage tracking, model-tier feedback loops, and agent-coordination signals

## Overview

Telemetry is how attune **measures itself**. The
`attune.telemetry` package records what every workflow run costs,
learns which model tier each workflow stage actually needs, and carries
the liveness signals that let multi-agent teams coordinate.

Three groups live here, all exported from `attune.telemetry`:

- **Usage tracking** — `UsageTracker` logs every LLM call (cost,
  tokens, cache hits, duration) to a local append-only store and rolls
  it up into stats and cost-savings reports.
- **Feedback loops** — `FeedbackLoop` records a quality score per
  workflow stage and tier, then recommends the cheapest tier that still
  meets the quality bar (`recommend_tier`).
- **Coordination signals** — `EventStreamer`, `HeartbeatCoordinator`,
  and `ApprovalGate` carry agent heartbeats, event streams, and
  human-in-the-loop approval requests for multi-agent runs. (These are
  telemetry in the "agent liveness/coordination" sense and also relate
  to orchestration.)

The data is **local-first**: `UsageTracker` writes under
`~/.attune/telemetry` (overridable via `ATTUNE_HOME`) and nothing here
calls the network unless an opt-in phone-home is explicitly enabled. The
`telemetry_stats` MCP tool and the ops dashboard read the same on-disk
store (`~/.attune/telemetry/usage.jsonl`).

## Concepts

### `UsageTracker` — the cost/usage ledger

`UsageTracker` is the per-process ledger of LLM calls. It buffers
records and writes them in batches to `~/.attune/telemetry`. Use the
process-wide singleton, or construct one directly with store knobs:
`UsageTracker(telemetry_dir=None, retention_days=90,
max_file_size_mb=10, buffer_size=50)`.

`track_llm_call(...)` is the record path — workflows call it for you
with the call's `workflow`, `stage`, `tier`, `model`, `provider`,
`cost`, `tokens`, cache flags, and `duration_ms`. `get_stats(days=30)`
rolls the store up; `calculate_savings(days=30)` reports cache/tier
savings; `get_recent_entries()`, `get_cache_stats()`, and
`export_to_dict()` read it back; `flush()` forces a write and `reset()`
clears it.

### `FeedbackLoop` — tier recommendation from quality scores

`FeedbackLoop` closes the cost/quality loop. You record a quality score
(0–1) for a workflow stage at the tier it ran on; once at least
`MIN_SAMPLES` (10) exist for that stage, it recommends a tier.
`QUALITY_THRESHOLD` is `0.7`; feedback entries expire after
`FEEDBACK_TTL` (604800 s = 7 days). Backing storage is the optional
`memory` passed to the constructor.

### `TelemetryFeatures` — feature/Redis status

`TelemetryFeatures` reports which telemetry features are available in
the current environment — chiefly whether the Redis-backed coordination
features are reachable. `list_all_features()` and
`get_feature_status()` enumerate status; `is_redis_available()` /
`require_redis()` gate the Redis-dependent paths.

### Coordination signals

`HeartbeatCoordinator` tracks agent liveness (`beat`,
`start_heartbeat`, `get_active_agents`, `get_stale_agents`,
`is_agent_alive`); `EventStreamer` publishes and consumes event streams
(`publish_event`, `consume_events`, `get_recent_events`); `ApprovalGate`
carries `ApprovalRequest` / `ApprovalResponse` for human-in-the-loop
steps. These back multi-agent coordination and are Redis-backed when
available.

## Notes & tips

- **Depend on the documented public surface.** The supported API is the
  classes exported from `attune.telemetry`; the per-module internals
  (file layout, buffering) are implementation details.
- **Use the singleton for reads.** `UsageTracker.get_instance()` reads
  the same store workflows write to; constructing a fresh tracker with a
  different `telemetry_dir` reads a different store.
- **`flush()` before reading freshly written calls.** Writes are
  buffered.
- **Coordination needs Redis.** Gate `EventStreamer` /
  `HeartbeatCoordinator` use behind `TelemetryFeatures`.
