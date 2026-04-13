---
feature: telemetry
depth: concept
generated_at: 2026-04-13T17:01:38.879778+00:00
source_hash: 295e5e35ecdbf0e851c8b1779b79738f03b705495583edbf2e6416bf4fe17480
status: generated
---

# Telemetry

## How it works

Telemetry tracks AI agent performance, coordinates multi-agent workflows, and provides human oversight controls for Attune AI operations.

The main building blocks are:

- **`CoordinationSignal`** — Coordination signal between agents.
- **`CoordinationSignals`** — TTL-based inter-agent coordination signals.
- **`AgentHeartbeat`** — Agent heartbeat data structure.
- **`HeartbeatCoordinator`** — Coordinates agent heartbeats using Redis TTL keys.
- **`ApprovalRequest`** — Approval request with context for human decision.

Under the hood, this feature spans 15 source
files covering:

- Agent coordination via TTL signals
- Agent heartbeat tracking system
- Human approval gates for workflow control

## What connects to it

This feature relates to: telemetry, metrics.

Other parts of the codebase interact with
telemetry through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `CoordinationSignal` | Coordination signal between agents. | `src/attune/telemetry/agent_coordination.py` |
| `CoordinationSignals` | TTL-based inter-agent coordination signals. | `src/attune/telemetry/agent_coordination.py` |
| `AgentHeartbeat` | Agent heartbeat data structure. | `src/attune/telemetry/agent_tracking.py` |
| `HeartbeatCoordinator` | Coordinates agent heartbeats using Redis TTL keys. | `src/attune/telemetry/agent_tracking.py` |
| `ApprovalRequest` | Approval request with context for human decision. | `src/attune/telemetry/approval_gates.py` |
