---
type: concept
name: telemetry-concept
feature: telemetry
depth: concept
generated_at: 2026-05-16T06:19:45.821122+00:00
source_hash: ed8485991002cc1c218f67b4f33f230bcbdc4325599a2e03f2bbe584d94a5e90
status: generated
---

# Telemetry

Attune's telemetry layer is an observability system that tracks agent activity, routes signals between agents, gates high-stakes actions on human approval, and records usage data to drive cost and quality feedback loops.

## What telemetry covers

Telemetry spans four distinct concerns that work together to keep multi-agent workflows visible and controllable:

| Concern | What it does | Key types |
|---|---|---|
| **Usage tracking** | Records help queries and calculates cost savings from prompt caching and model-tier routing | `UsageTracker`, `FeedbackLoop` |
| **Agent heartbeats** | Publishes liveness signals to Redis TTL keys so you can detect stale or crashed agents | `HeartbeatCoordinator`, `AgentHeartbeat` |
| **Inter-agent coordination** | Routes typed signals between agents with configurable TTLs; expired signals are discarded automatically | `CoordinationSignals`, `CoordinationSignal` |
| **Human approval gates** | Pauses a workflow until a human responds to an `ApprovalRequest`; times out if no response arrives within `timeout_seconds` | `ApprovalGate`, `ApprovalRequest`, `ApprovalResponse` |

A fifth concern — real-time event streaming — cuts across all four: `EventStreamer` publishes `StreamEvent` records to Redis Streams so external consumers can observe what is happening without polling.

## How the pieces fit together

Think of telemetry as three concentric layers:

1. **Signal transport.** `CoordinationSignals` and `EventStreamer` move data between agents and between agents and humans. Signals carry a `ttl_seconds` field (default 60); the Redis TTL key expires the signal automatically so stale coordination state never accumulates.

2. **Liveness.** `HeartbeatCoordinator` writes an `AgentHeartbeat` record on each call to `beat()`. The record includes `status`, `progress` (0.0–1.0), and `current_task`. Calling `get_stale_agents(threshold_seconds=60.0)` returns agents whose last beat is older than the threshold — a concrete way to detect a hung agent without building custom polling logic.

3. **Control.** `ApprovalGate.request_approval()` blocks until a human calls `respond_to_approval()` or the request times out. The `ApprovalResponse` carries `approved: bool` and an optional `reason`, giving the workflow a typed branch point rather than an ambiguous string.

Usage data recorded by `UsageTracker` and quality scores from `FeedbackLoop` sit alongside these runtime signals. The CLI commands (`cmd_telemetry_show`, `cmd_telemetry_savings`, `cmd_telemetry_cache_stats`, `cmd_agent_performance`) surface that data without requiring direct access to the underlying storage.

## When telemetry matters

Telemetry becomes important in three scenarios:

- **Multi-agent pipelines.** When several agents run concurrently, `CoordinationSignals.broadcast()` lets one agent notify all others of a state change (for example, that a shared resource is ready) without knowing how many listeners exist.
- **Long-running tasks.** `HeartbeatCoordinator` makes it straightforward to answer "is this agent still alive?" by checking `is_agent_alive(agent_id)` or listing stale agents with `get_stale_agents()`.
- **Sensitive or irreversible actions.** Wrapping an action in `ApprovalGate.request_approval()` inserts a human checkpoint. If the timeout expires before a response arrives, the gate returns a typed `ApprovalResponse` with `approved: False` so the workflow can handle the timeout explicitly.

## Related topics

- **Concept**: Feedback loop — how `record_template_feedback()` and `get_template_confidence()` use accumulated ratings to rank templates
- **Reference**: Telemetry — field-level documentation for `CoordinationSignal`, `AgentHeartbeat`, `ApprovalRequest`, and `StreamEvent`
