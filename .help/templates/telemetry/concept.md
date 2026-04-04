---
feature: telemetry
depth: concept
generated_at: 2026-04-04T02:25:50.579374+00:00
source_hash: cdb506bfba26d96b90402bbc00b19c3dd80afaec88f6a4ae5de0c1c585b63162
status: generated
---

# Telemetry

## What

Usage tracking and feedback loops

## Why

This feature provides telemetry functionality for the project.

## How

Key components:

- `CoordinationSignal` — Coordination signal between agents.

- `CoordinationSignals` — TTL-based inter-agent coordination signals.

- `AgentHeartbeat` — Agent heartbeat data structure.

- `HeartbeatCoordinator` — Coordinates agent heartbeats using Redis TTL keys.

- `ApprovalRequest` — Approval request with context for human decision.
