---
type: note
feature: telemetry
depth: note
generated_at: 2026-04-14T15:21:50.382946+00:00
source_hash: 295e5e35ecdbf0e851c8b1779b79738f03b705495583edbf2e6416bf4fe17480
status: generated
---

# Note: telemetry

## Context

The telemetry module provides real-time monitoring, coordination, and human oversight capabilities for Attune AI agents. It implements three core subsystems: inter-agent coordination using TTL signals, heartbeat tracking for agent lifecycle monitoring, and approval gates for human workflow control.

## Architecture

The telemetry system is built around Redis for persistence and real-time capabilities. Each subsystem operates independently but shares the same Redis memory backend:

**Agent Coordination** uses TTL-based signals for inter-agent communication. The `CoordinationSignals` class manages signal creation, broadcasting, and consumption with automatic expiration. Signals can target specific agents or broadcast to all agents, with configurable time-to-live values.

**Agent Tracking** monitors agent health through periodic heartbeats. The `HeartbeatCoordinator` class tracks agent status, progress, and current tasks. It automatically detects stale agents and provides real-time visibility into the agent population.

**Approval Gates** implement human-in-the-loop workflow control. The `ApprovalGate` class creates approval requests that require human intervention before agents can proceed. Requests include context data and configurable timeouts.

**Event Streaming** provides real-time event publishing and consumption using Redis Streams. The `EventStreamer` class enables agents and external systems to publish events and subscribe to event streams with configurable filtering.

## CLI Integration

The module includes a comprehensive CLI interface accessed through `python -m attune.telemetry`. The CLI provides analytics commands for cost analysis (`cmd_sonnet_opus_analysis`), test status reporting (`cmd_file_test_status`, `cmd_test_status`), automation metrics (`cmd_tier1_status`, `cmd_task_routing_report`), and agent performance monitoring (`cmd_agent_performance`).

## Data Structures

All telemetry data uses structured dataclasses with JSON serialization support. `CoordinationSignal`, `AgentHeartbeat`, `ApprovalRequest`, and `StreamEvent` provide consistent interfaces for data exchange between agents and external monitoring systems.

**Tags:** `telemetry`, `metrics`
