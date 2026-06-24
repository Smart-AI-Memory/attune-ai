---
feature: telemetry
summary: Usage tracking, model-tier feedback loops, and agent-coordination signals
tags: [telemetry, metrics]
source_globs:
  - src/attune/telemetry/**
nav:
  help: telemetry
  mkdocs:
    how-to: how-to/telemetry
    architecture: architecture/telemetry
    reference: reference/telemetry
---

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

## Comparison

Telemetry is the **measurement** layer, distinct from the surfaces that
read it:

| | telemetry | ops-dashboard | usage-signals phone-home |
|--|-----------|---------------|--------------------------|
| Role | Records usage/quality/coordination | Renders it in a local web UI | Optionally reports anonymized signal |
| Locality | Local store under `~/.attune/telemetry` | Reads the local store | Network, opt-in only |
| Entry | `UsageTracker` / `FeedbackLoop` | `python -m attune.ops` | Consent-gated client |

`UsageTracker` answers "what did it cost"; `FeedbackLoop` answers "what
tier should this stage use"; the coordination classes answer "which
agents are alive."

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

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic source
> of truth fed by four channels — unmatched user queries, telemetry
> error-frequency, GitHub issues, and these author-curated seeds —
> merged, deduplicated, and frequency-ranked by the FAQ Generator. This
> section is **not** projected verbatim; it contributes the feature's
> author-curated seed questions.

- **Q:** What does attune telemetry record?
  **A:** Every LLM call's cost/tokens/cache/duration (`UsageTracker`),
  a quality score per workflow stage and tier (`FeedbackLoop`), and
  agent coordination signals (`EventStreamer`, `HeartbeatCoordinator`).
- **Q:** Where is the data stored?
  **A:** Locally under `~/.attune/telemetry`. Nothing leaves your
  machine unless you enable an opt-in phone-home.
- **Q:** How do I see my usage/metrics?
  **A:** `UsageTracker.get_instance().get_stats(days=30)` from Python,
  the `telemetry_stats` MCP tool from a conversation, or the ops
  dashboard.
- **Q:** Why won't the feedback loop change my tier?
  **A:** It needs at least `MIN_SAMPLES` (10) feedback rows for a stage
  before `recommend_tier` will move off the current tier.

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

## Design & extension

### Design decisions

- **Local-first, opt-in phone-home.** Usage data is written locally;
  any network reporting is a separate, consent-gated path.
- **Append-only, batched, retention-bounded.** `UsageTracker` buffers
  and rolls files, bounded by `retention_days` / `max_file_size_mb`, so
  the store stays small without losing recent fidelity.
- **Conservative tier feedback.** `FeedbackLoop` requires
  `MIN_SAMPLES` and a `QUALITY_THRESHOLD` before it recommends a change,
  so a single bad score can't downgrade a stage.
- **Redis-optional coordination.** Heartbeats and event streams use
  Redis when present; `TelemetryFeatures` reports availability so
  callers degrade gracefully.

### Extension points

- **Read the data your own way:** `UsageTracker.export_to_dict()` /
  `get_recent_entries()`.
- **Feed the loop:** call `FeedbackLoop.record_feedback(...)` from a
  custom workflow stage.
- **Coordinate custom agents:** publish via `EventStreamer` and beat
  via `HeartbeatCoordinator` (Redis required).
