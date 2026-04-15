---
type: warning
feature: telemetry
depth: warning
generated_at: 2026-04-14T15:20:43.753236+00:00
source_hash: 295e5e35ecdbf0e851c8b1779b79738f03b705495583edbf2e6416bf4fe17480
status: generated
---

# Telemetry cautions

## What to watch for

The telemetry system manages agent coordination, heartbeats, and approval workflows through Redis-backed TTL mechanisms. These distributed operations can create timing-dependent failures and memory leaks if not handled carefully.

## Risk areas

### TTL signal expiration in multi-agent coordination

`CoordinationSignals.wait_for_signal()` blocks for up to 30 seconds by default, but signals expire after 60 seconds. If your polling interval is too long or network delays occur, you may miss signals that were sent but expired before consumption.

**Risk:** Agents wait indefinitely for coordination signals that have already expired, causing workflow deadlocks.

**Mitigation:** Set `ttl_seconds` longer than your expected `timeout` duration, and always handle `None` returns from `wait_for_signal()`.

### Heartbeat coordinator memory accumulation

`HeartbeatCoordinator.start_heartbeat()` creates Redis keys with TTL, but `stop_heartbeat()` only sets final status—it doesn't clean up the key. Agents that crash without calling `stop_heartbeat()` leave stale entries that accumulate over time.

**Risk:** Redis memory grows unbounded from abandoned heartbeat keys, eventually causing storage exhaustion.

**Mitigation:** Use `get_stale_agents()` periodically to identify and clean up expired heartbeats, or set shorter heartbeat TTLs relative to your monitoring intervals.

### Approval request timeouts without cleanup

`ApprovalGate.request_approval()` creates approval requests with timeouts, but expired requests remain in storage until manually cleared with `clear_expired_requests()`. This method is not called automatically.

**Risk:** Pending approval queues grow indefinitely, consuming memory and making approval dashboards unusable.

**Mitigation:** Run `clear_expired_requests()` on a schedule, or implement automatic cleanup in your approval monitoring workflow.

### Event stream unbounded growth

`EventStreamer.publish_event()` appends to Redis Streams without automatic trimming. High-volume event publishing can cause streams to grow to hundreds of thousands of entries.

**Risk:** Redis memory exhaustion and degraded stream read performance as event history accumulates.

**Mitigation:** Call `trim_stream()` regularly to limit stream length, or set up Redis Stream MAXLEN policies at the infrastructure level.

## How to avoid problems

1. **Set explicit TTLs for all coordination primitives.** Don't rely on default TTL values—calculate them based on your actual workflow timing requirements and add buffer time for network delays.

2. **Implement cleanup routines for long-running systems.** Schedule periodic calls to `clear_expired_requests()`, `get_stale_agents()`, and `trim_stream()` to prevent memory accumulation in production deployments.

3. **Handle timeout scenarios gracefully.** All `wait_for_signal()`, `request_approval()`, and event consumption operations can return `None` or empty results due to timeouts—design your workflows to recover or escalate rather than hanging indefinitely.

4. **Monitor Redis memory usage.** The telemetry system creates many ephemeral keys that should expire automatically. If Redis memory grows steadily, investigate TTL settings and cleanup routines first.

## Source files

- `src/attune/telemetry/**`

**Tags:** `telemetry`, `metrics`
