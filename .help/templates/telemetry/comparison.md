---
type: comparison
feature: telemetry
depth: comparison
generated_at: 2026-04-14T15:22:03.502665+00:00
source_hash: 295e5e35ecdbf0e851c8b1779b79738f03b705495583edbf2e6416bf4fe17480
status: generated
---

# Telemetry vs manual tracking approaches

## Context

The telemetry feature provides structured agent coordination, heartbeat monitoring, and approval gates. You can build these capabilities yourself, but the telemetry module handles TTL-based coordination, Redis streaming, and workflow approval patterns out of the box.

## Feature comparison

| Capability | Telemetry module | Manual implementation | Custom Redis usage |
|------------|------------------|----------------------|-------------------|
| Agent coordination | `CoordinationSignals` with TTL and broadcast | Custom message passing | Raw Redis pub/sub |
| Heartbeat tracking | `HeartbeatCoordinator` with automatic TTL | Manual status polling | Redis key expiration |
| Approval workflows | `ApprovalGate` with timeout handling | Custom request/response | Manual state tracking |
| Event streaming | `EventStreamer` with Redis Streams | Custom event bus | Direct stream commands |
| Data persistence | Automatic Redis integration | Your storage choice | Redis configuration required |
| Error handling | Built-in timeouts and cleanup | Manual error cases | Raw Redis exceptions |

## When to use telemetry

Use the telemetry module when you need:

- **Multi-agent coordination**: TTL-based signals prevent stale coordination state
- **Health monitoring**: Automatic agent heartbeat tracking with Redis TTL cleanup
- **Human-in-the-loop workflows**: Approval gates with configurable timeouts
- **Real-time event tracking**: Redis Streams for performance and cost analysis

The CLI commands show telemetry's reporting strength:
- `cmd_sonnet_opus_analysis()` — Model fallback cost analysis
- `cmd_agent_performance()` — Agent performance metrics
- `cmd_telemetry_cache_stats()` — Prompt caching statistics

## When NOT to use it

Skip telemetry when:

- **Simple scripts**: Single-agent tasks don't need coordination overhead
- **Custom storage requirements**: Telemetry assumes Redis; file-based or database storage requires manual implementation
- **High-frequency events**: Redis Streams have throughput limits; consider direct logging for >1000 events/sec
- **Offline operation**: All telemetry features require Redis connectivity

## Recommended approach

**Use telemetry when** you have multiple agents that need to coordinate, track health status, or require approval workflows. The Redis TTL patterns handle cleanup automatically.

**Use manual tracking when** you have simple single-agent workflows, need custom storage backends, or require offline operation.

**Use direct Redis when** telemetry's abstractions don't fit your coordination pattern, but you still want Redis performance.

## Source files

- `src/attune/telemetry/**`

**Tags:** `telemetry`, `metrics`
