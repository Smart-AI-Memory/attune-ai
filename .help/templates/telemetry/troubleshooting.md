---
type: troubleshooting
feature: telemetry
depth: troubleshooting
generated_at: 2026-04-14T15:21:05.112801+00:00
source_hash: 295e5e35ecdbf0e851c8b1779b79738f03b705495583edbf2e6416bf4fe17480
status: generated
---

# Troubleshoot telemetry

## Before you start

The telemetry feature provides agent coordination, heartbeat tracking, approval workflows, and real-time event streaming for Attune AI. Issues typically manifest as missed signals, stale heartbeats, blocked approvals, or streaming failures.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Agents not coordinating or missing signals | Redis connection and TTL expiration in `CoordinationSignals.check_signal()` |
| Heartbeat shows agents as offline when they're running | TTL key expiration in Redis and `HeartbeatCoordinator.beat()` call frequency |
| Approval requests hang indefinitely | Request timeout settings and `ApprovalGate.get_pending_approvals()` |
| Events missing from streams | Redis Stream availability and `EventStreamer.publish_event()` return values |
| CLI commands return no data | Redis connectivity and data retention policies |

## Step-by-step diagnosis

1. **Verify Redis connectivity.**
   Most telemetry failures stem from Redis issues. Test the connection:
   ```bash
   redis-cli ping
   ```
   If Redis is unreachable, check your connection configuration and ensure the Redis server is running.

2. **Check TTL behavior for coordination signals.**
   Coordination signals expire after their TTL period. Verify signal timing:
   ```python
   signals = CoordinationSignals()
   pending = signals.get_pending_signals()
   print(f"Found {len(pending)} unexpired signals")
   ```

3. **Inspect heartbeat TTL keys.**
   Agent heartbeats use Redis TTL keys. Check if heartbeats are being sent frequently enough:
   ```python
   coordinator = HeartbeatCoordinator()
   active = coordinator.get_active_agents()
   stale = coordinator.get_stale_agents(threshold_seconds=60)
   ```

4. **Test approval gate timeouts.**
   Approval requests have configurable timeouts. Check for expired requests:
   ```python
   gate = ApprovalGate()
   expired_count = gate.clear_expired_requests()
   pending = gate.get_pending_approvals()
   ```

5. **Examine event stream health.**
   Event streaming relies on Redis Streams. Check stream info:
   ```python
   streamer = EventStreamer()
   info = streamer.get_stream_info("your_event_type")
   ```

6. **Run telemetry CLI diagnostics.**
   Use built-in commands to check system status:
   ```bash
   python -m attune.telemetry telemetry-show
   python -m attune.telemetry agent-performance
   ```

## Common fixes

- **Increase heartbeat frequency.** If agents appear offline, reduce the interval between `HeartbeatCoordinator.beat()` calls to less than the TTL threshold (default 60 seconds).

- **Extend signal TTL.** For slow operations, increase `ttl_seconds` when calling `CoordinationSignals.signal()` or `broadcast()`.

- **Clear expired data.** Remove stale signals and approval requests:
  ```python
  signals.clear_signals()  # Clear all signals
  gate.clear_expired_requests()  # Remove timed-out approvals
  ```

- **Restart Redis connection.** Connection issues may require reinitializing the Redis client. This often requires restarting your application.

- **Trim large streams.** Event streams can grow large. Trim them periodically:
  ```python
  streamer.trim_stream("event_type", max_length=1000)
  ```

- **Check Redis memory limits.** Redis may evict data when memory is full. Verify your Redis memory configuration and eviction policies.

## Source files

- `src/attune/telemetry/**`

**Tags:** `telemetry`, `metrics`
