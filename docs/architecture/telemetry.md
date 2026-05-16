# Telemetry architecture

Runtime observability for Attune AI agents.

## Purpose

The telemetry subsystem records what agents are doing, routes coordination signals between them, gates workflow steps on human approval, streams events in real time, and feeds quality scores back to the model-tier selection logic. It does **not** handle prompt construction, workflow scheduling, or LLM API calls — those remain in their respective subsystems. Keeping this boundary clean means you can add a new tracking mechanism or swap the Redis backend without touching agent or workflow code.

## Key classes

| Class | Responsibility | File |
|-------|---------------|------|
| `CoordinationSignal` | Dataclass envelope for a single inter-agent signal, including TTL, source/target agents, and an arbitrary payload. | `src/attune/telemetry/agent_coordination.py` |
| `CoordinationSignals` | Writes, broadcasts, and consumes `CoordinationSignal` records backed by TTL-expiring Redis keys. | `src/attune/telemetry/agent_coordination.py` |
| `AgentHeartbeat` | Dataclass snapshot of one agent's liveness state: status, progress float, and current task string. | `src/attune/telemetry/agent_tracking.py` |
| `HeartbeatCoordinator` | Manages per-agent heartbeat keys in Redis; detects stale agents via a configurable threshold. | `src/attune/telemetry/agent_tracking.py` |
| `ApprovalRequest` | Dataclass representing a pending human-approval gate, including a timeout and current status field. | `src/attune/telemetry/approval_gates.py` |
| `ApprovalResponse` | Dataclass carrying the human's approved/rejected decision and an optional reason string. | `src/attune/telemetry/approval_gates.py` |
| `ApprovalGate` | Issues approval requests, polls for responses, and expires timed-out requests from the pending queue. | `src/attune/telemetry/approval_gates.py` |
| `StreamEvent` | Dataclass envelope for a single Redis Streams entry: event type, timestamp, and data payload. | `src/attune/telemetry/event_streaming.py` |
| `EventStreamer` | Publishes `StreamEvent` records and exposes blocking/non-blocking consumers; also manages stream lifecycle (trim, delete). | `src/attune/telemetry/event_streaming.py` |
| `FeatureStatus` | Enum-like status value for a single optional telemetry capability. | `src/attune/telemetry/features.py` |
| `FeatureInfo` | Holds the name, status, and descriptive metadata for one telemetry feature. | `src/attune/telemetry/features.py` |
| `TelemetryFeatures` | Queries which telemetry features (e.g., streaming, heartbeat) are available in the current environment. | `src/attune/telemetry/features.py` |
| `FeedbackLoop` | Records per-response quality feedback and translates accumulated scores into model-tier recommendations. | `src/attune/telemetry/feedback_loop.py` |
| `ModelTier` | Mirrors `workflows.base.ModelTier`; kept local so telemetry has no hard dependency on the workflows package. | `src/attune/telemetry/feedback_models.py` |
| `FeedbackEntry` | Dataclass for one quality rating attached to a single LLM response. | `src/attune/telemetry/feedback_models.py` |
| `QualityStats` | Aggregates `FeedbackEntry` records into per-stage statistics (counts, mean score). | `src/attune/telemetry/feedback_models.py` |
| `TierRecommendation` | Carries a `ModelTier` recommendation derived from `QualityStats`, with a confidence value. | `src/attune/telemetry/feedback_models.py` |
| `HelpTracker` | Appends help-system query records to a JSONL file (`help_queries.jsonl`); append-only, no reads. | `src/attune/telemetry/help_tracker.py` |
| `UsageTracker` | Privacy-first local tracker that logs usage events without sending data off-device. | `src/attune/telemetry/usage_tracker.py` |

## Data flow

Two largely independent flows converge on Redis, plus a local-only path for help and usage logging:

```
Agent process
│
├─ HeartbeatCoordinator ──── beat() ──────────────────► Redis TTL key
│                                                        (expires if agent dies)
│
├─ CoordinationSignals ───── signal() / broadcast() ──► Redis TTL key
│                        ◄── wait_for_signal() ─────────
│
├─ ApprovalGate ──────────── request_approval() ──────► Redis (pending queue)
│                        ◄── respond_to_approval() ─────
│
└─ EventStreamer ──────────── publish_event() ─────────► Redis Stream
                         ◄── consume_events() ───────────

LLM response
│
└─ FeedbackLoop
     │  record(FeedbackEntry)
     ▼
   FeedbackEntry[]  ──► QualityStats  ──► TierRecommendation
                                            (Sonnet ↔ Opus routing)

Agent process (help / usage, local only)
│
├─ HelpTracker  ──► help_queries.jsonl  (append-only)
└─ UsageTracker ──► local telemetry store  (no network)
```

`TelemetryFeatures` is queried at startup to determine which of the Redis-backed paths are available before any of the above runs.

## Design decisions

**Local mirror of `ModelTier`**: `feedback_models.py` defines its own `ModelTier` rather than importing from `workflows.base`. This avoids a circular dependency between the telemetry and workflows packages. If the canonical enum changes, both copies must be kept in sync — an intentional trade-off documented here so the next maintainer knows the duplication is load-bearing.

**TTL as the liveness mechanism**: `CoordinationSignals` and `HeartbeatCoordinator` both rely on Redis TTL expiry rather than explicit deletion to clean up after dead agents. This means the absence of a key is the signal — no separate garbage-collection process is needed, but it also means a Redis restart clears all liveness state.

**Approval gate is synchronous from the requester's perspective**: `ApprovalGate.request_approval()` blocks until a response arrives or the timeout expires. This keeps agent workflow code simple (no callback wiring), at the cost of holding a thread during the wait window.

## Extension points

- **Add a new coordination signal type**: call `CoordinationSignals.signal()` or `CoordinationSignals.broadcast()` with a new `signal_type` string. No class changes are required; the payload is an arbitrary `dict`.
- **Track a new agent metric**: add fields to `AgentHeartbeat` and pass them through `HeartbeatCoordinator.beat()`. Both are dataclasses, so adding fields is straightforward.
- **Add a new approval workflow**: call `ApprovalGate.request_approval()` with a new `approval_type` string; the gate stores and routes requests by that type without requiring subclassing.
- **Consume events in a new service**: construct an `EventStreamer` and call `consume_events()` with the event types you care about. Publishing requires only `publish_event()` — there is no registry to update.
- **Add a quality-feedback stage**: create `FeedbackEntry` records for the new stage and pass them to `FeedbackLoop`. `QualityStats` aggregates by stage name, so no schema changes are needed.
- **Disable Redis-backed features gracefully**: check `TelemetryFeatures` at startup and skip the Redis-dependent paths if the relevant feature reports unavailable.
