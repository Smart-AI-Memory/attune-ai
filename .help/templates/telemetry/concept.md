---
type: concept
feature: telemetry
depth: concept
generated_at: 2026-04-14T15:19:17.136636+00:00
source_hash: 295e5e35ecdbf0e851c8b1779b79738f03b705495583edbf2e6416bf4fe17480
status: generated
---

# Telemetry

The telemetry system enables real-time monitoring and coordination across Attune AI's multi-agent workflows through Redis-backed tracking, signaling, and approval mechanisms.

## Core architecture

The telemetry system operates on three foundational patterns: TTL-based signals for agent coordination, heartbeat tracking for liveness monitoring, and approval gates for human oversight. All components use Redis as a shared coordination layer, allowing agents to communicate without direct dependencies.

**Agent coordination** happens through `CoordinationSignals`, which send TTL-expiring messages between specific agents or broadcast to all agents. For example, when one agent completes a file analysis, it can signal completion to the next agent in the pipeline using `signal("analysis_complete", target_agent="reviewer")`.

**Heartbeat tracking** monitors agent health through `HeartbeatCoordinator`, which maintains Redis keys that expire if agents stop reporting. Each agent calls `beat(status="processing", progress=0.75)` periodically, and the coordinator can identify stale agents that haven't reported within a threshold.

**Approval gates** pause workflows for human decisions through `ApprovalGate`. When an agent needs approval for a sensitive operation, it creates an `ApprovalRequest` with context and waits for a human response through `request_approval("deploy_changes", context={"files": ["config.py"]})`.

## Event streaming and CLI reporting

The `EventStreamer` publishes workflow events to Redis Streams for real-time monitoring, while the CLI commands provide operational visibility into system performance. Commands like `cmd_agent_performance` and `cmd_telemetry_savings` extract metrics from the telemetry data to show cost savings, test status, and agent performance across the system.

## Integration points

Other parts of the codebase interact with telemetry through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `CoordinationSignal` | Coordination signal between agents. | `src/attune/telemetry/agent_coordination.py` |
| `CoordinationSignals` | TTL-based inter-agent coordination signals. | `src/attune/telemetry/agent_coordination.py` |
| `AgentHeartbeat` | Agent heartbeat data structure. | `src/attune/telemetry/agent_tracking.py` |
| `HeartbeatCoordinator` | Coordinates agent heartbeats using Redis TTL keys. | `src/attune/telemetry/agent_tracking.py` |
| `ApprovalRequest` | Approval request with context for human decision. | `src/attune/telemetry/approval_gates.py` |
