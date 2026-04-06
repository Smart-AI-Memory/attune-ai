---
feature: telemetry
depth: concept
generated_at: 2026-04-06T04:34:57.382786+00:00
source_hash: cdb506bfba26d96b90402bbc00b19c3dd80afaec88f6a4ae5de0c1c585b63162
status: generated
---

# Telemetry

## How it works

Telemetry tracking for Attune AI, with agent coordination and human approval gates.

The main building blocks are:

- **`CoordinationSignal`** — Coordination signal between agents.
- **`CoordinationSignals`** — TTL-based inter-agent coordination signals.
- **`AgentHeartbeat`** — Agent heartbeat data structure.
- **`HeartbeatCoordinator`** — Coordinates agent heartbeats using Redis TTL keys.
- **`ApprovalRequest`** — Approval request with context for human decision.

Under the hood, this feature spans 33 source
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
