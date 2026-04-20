---
type: warning
feature: telemetry
depth: warning
generated_at: 2026-04-20T01:24:07.636626+00:00
source_hash: 6acf95560dfe49824641ad827861534eaea26c9226d58caa5c047e5a5c955c0d
status: generated
---

# Telemetry Cautions

## What to watch for

Agent coordination signals and heartbeat tracking can create race conditions when agents share state across Redis TTL keys.

## Risk areas

### Coordination signal timing

`CoordinationSignals.wait_for_signal()` polls Redis with a default 0.5-second interval. Under high load, signals can expire before slow consumers read them, causing agents to hang indefinitely waiting for coordination that already happened.

**Mitigation:** Set conservative TTL values (`ttl_seconds=300` instead of the default 60) for critical coordination points, and always specify shorter timeouts for `wait_for_signal()` calls.

### Heartbeat coordinator state drift

`HeartbeatCoordinator.get_stale_agents()` relies on Redis TTL expiration, but network partitions or Redis failover can make agents appear stale when they're actually running. This leads to duplicate work or failed coordination.

**Mitigation:** Cross-check heartbeat status with multiple signals before marking an agent as failed. Use `is_agent_alive()` as a secondary confirmation rather than relying solely on `get_stale_agents()`.

### Approval gate deadlocks

`ApprovalGate.request_approval()` blocks indefinitely if no human responder is available and the timeout isn't set. Multiple agents waiting for approval can exhaust connection pools or cause cascade failures.

**Mitigation:** Always set explicit timeouts (`timeout=300.0` for 5-minute maximum wait) and implement fallback behavior when approvals time out.

### Event stream memory growth

`EventStreamer.publish_event()` writes to unbounded Redis streams that grow indefinitely unless trimmed. High-frequency telemetry events can exhaust Redis memory in production environments.

**Mitigation:** Configure automatic stream trimming with `trim_stream(max_length=1000)` or implement retention policies based on event age rather than count.

## How to avoid problems

1. **Test coordination under load.** Run multiple agent instances against shared Redis to verify signal timing works under realistic conditions.

2. **Monitor Redis memory usage.** Set up alerts for stream length and TTL key counts to catch runaway telemetry before it affects other systems.

3. **Use explicit timeouts everywhere.** Never rely on default timeout values for coordination primitives—always specify limits based on your workflow's requirements.

## Source files

- `src/attune/telemetry/**`
