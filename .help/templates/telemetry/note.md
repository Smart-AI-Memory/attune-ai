---
type: note
feature: telemetry
depth: note
generated_at: 2026-04-20T01:25:16.410611+00:00
source_hash: 6acf95560dfe49824641ad827861534eaea26c9226d58caa5c047e5a5c955c0d
status: generated
---

# Note: telemetry

## Context

The telemetry feature provides usage tracking and feedback loops for Attune AI. It enables distributed agent coordination through TTL signals, heartbeat monitoring for agent health, human approval gates for workflow control, and real-time event streaming.

## Content

The telemetry system consists of four main components:

**Agent coordination** manages communication between distributed agents using Redis TTL keys. The `CoordinationSignals` class handles signal broadcasting and consumption, while `CoordinationSignal` represents individual messages with automatic expiration.

**Agent tracking** monitors the health and status of running agents. `HeartbeatCoordinator` manages periodic status updates, and `AgentHeartbeat` stores agent state including progress, current task, and metadata.

**Approval gates** pause workflows for human decisions. `ApprovalGate` creates approval requests that require manual intervention, using `ApprovalRequest` and `ApprovalResponse` to manage the interaction flow.

**Event streaming** provides real-time telemetry through Redis Streams. `EventStreamer` publishes and consumes events, with `StreamEvent` representing individual telemetry data points.

The CLI interface exposes analysis and automation status through functions like `cmd_sonnet_opus_analysis()` for cost tracking and `cmd_tier1_status()` for automation health monitoring.

## Source files

The implementation spans 16 files under `src/attune/telemetry/`, with the main entry point at `__main__.py` and component-specific modules for coordination, tracking, approval gates, and streaming functionality.
