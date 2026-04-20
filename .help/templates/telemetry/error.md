---
type: error
feature: telemetry
depth: error
generated_at: 2026-04-20T01:23:53.194937+00:00
source_hash: 6acf95560dfe49824641ad827861534eaea26c9226d58caa5c047e5a5c955c0d
status: generated
---

# Telemetry errors

Failures in agent coordination, heartbeat tracking, approval workflows, and event streaming components.

## Common error signatures

- **Redis connection failures**: `redis.exceptions.ConnectionError` when coordination signals, heartbeats, or event streams can't connect to Redis
- **Signal timeout errors**: `TimeoutError` when `wait_for_signal()` exceeds the specified timeout without receiving a coordination signal
- **TTL expiration**: Stale agent heartbeats or expired coordination signals causing coordination failures
- **Serialization errors**: `json.JSONDecodeError` when deserializing coordination signals, heartbeat data, or approval requests from Redis
- **Approval timeout**: Approval requests timing out before human response in `request_approval()`
- **Stream consumption errors**: Redis stream read failures in `consume_events()` or missing event types

## Where errors originate

Telemetry errors typically stem from these coordination and tracking components:

- **CoordinationSignals** — TTL-based signal exchange between agents fails due to Redis connectivity or signal expiration
- **HeartbeatCoordinator** — Agent heartbeat registration and monitoring fails when Redis keys expire or agents become unreachable
- **ApprovalGate** — Human approval workflows fail when requests timeout or response serialization breaks
- **EventStreamer** — Real-time event publishing and consumption fails due to Redis stream errors or malformed events
- **CLI commands** (`cmd_*` functions) — Telemetry reporting commands fail when underlying data sources are unavailable

## How to diagnose

1. **Check Redis connectivity first.** Most telemetry failures trace back to Redis connection issues. Verify Redis is running and accessible from your agent environment.

2. **Examine TTL timing.** If coordination signals or heartbeats are missing, check if TTL values are too short for your network latency. Default signal TTL is 60 seconds.

3. **Validate serialization data.** When you see `JSONDecodeError`, inspect the raw Redis data to identify which component is storing malformed JSON.

4. **Monitor approval timeouts.** For approval workflow failures, check if timeout values in `request_approval()` match your expected human response time.

5. **Trace event stream IDs.** Event streaming errors often involve Redis stream ID conflicts or attempts to read from non-existent streams.

## Source files

- `src/attune/telemetry/**`

**Tags:** `telemetry`, `metrics`
