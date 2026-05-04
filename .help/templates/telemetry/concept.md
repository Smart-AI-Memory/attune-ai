---
type: concept
feature: telemetry
depth: concept
generated_at: 2026-05-04T02:37:13.475757+00:00
source_hash: ed8485991002cc1c218f67b4f33f230bcbdc4325599a2e03f2bbe584d94a5e90
status: generated
---

# Telemetry

Telemetry is the monitoring and coordination system that tracks agent behavior, enables inter-agent communication, and provides human oversight controls for Attune AI workflows.

## What it tracks

The telemetry system monitors three layers of agent activity:

**Agent heartbeats** track whether agents are alive and what they're doing. Each agent sends periodic status updates including current task progress and metadata. The `HeartbeatCoordinator` uses Redis TTL keys to detect when agents stop responding, providing a real-time view of the agent ecosystem's health.

**Inter-agent coordination** enables agents to signal each other through time-limited messages. The `CoordinationSignals` class manages TTL-based communication where agents can broadcast status updates, request assistance, or coordinate handoffs. These signals automatically expire to prevent stale coordination data.

**Human approval gates** pause workflows when human oversight is required. The `ApprovalGate` system presents context-rich approval requests that humans can approve or reject, with configurable timeouts to prevent workflows from hanging indefinitely.

## Real-time streaming

Events flow through Redis Streams via the `EventStreamer`, which publishes structured events as they occur. This enables real-time monitoring dashboards and allows external systems to react to agent behavior changes immediately.

## Cost and performance insights

The telemetry CLI provides operational visibility through several reporting commands:
- Model tier fallback analysis shows cost savings from Sonnet 3.5 → Opus 3.5 degradation
- Test execution status tracks which files have passing automation
- Task routing reports show how work flows between agents
- Prompt caching statistics reveal performance optimizations

## Data structures

All telemetry data uses structured dataclasses that serialize to/from dictionaries for Redis storage:

| Class | Purpose | Key fields |
|-------|---------|------------|
| `CoordinationSignal` | Agent-to-agent messages | `signal_type`, `source_agent`, `target_agent`, `ttl_seconds` |
| `AgentHeartbeat` | Agent status updates | `agent_id`, `status`, `progress`, `current_task` |
| `ApprovalRequest` | Human approval requests | `approval_type`, `context`, `timeout_seconds` |
| `StreamEvent` | Real-time event notifications | `event_type`, `data`, `timestamp` |

This structured approach ensures telemetry data remains queryable and consistent as the agent ecosystem scales.
