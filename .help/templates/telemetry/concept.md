---
feature: telemetry
depth: concept
generated_at: 2026-05-12T20:01:25.969321+00:00
source_hash: 590fd017f021732dc1cad2f715e7eaaa2a436b4e8d7cd0434769d62d180dd966
status: generated
---

# Telemetry

## How it works

Usage tracking and feedback loops.

The main building blocks are:

- **`CoordinationSignal`** — Coordination signal between agents.
- **`CoordinationSignals`** — TTL-based inter-agent coordination signals.
- **`AgentHeartbeat`** — Agent heartbeat data structure.
- **`HeartbeatCoordinator`** — Coordinates agent heartbeats using Redis TTL keys.
- **`ApprovalRequest`** — Approval request with context for human decision.

Under the hood, this feature spans 16 source
files covering:

- Enable running telemetry as a module.
- Agent Coordination via TTL Signals.
- Agent Heartbeat Tracking System.

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
