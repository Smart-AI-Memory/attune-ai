---
type: error
feature: telemetry
depth: error
generated_at: 2026-04-14T15:20:26.920471+00:00
source_hash: 295e5e35ecdbf0e851c8b1779b79738f03b705495583edbf2e6416bf4fe17480
status: generated
---

# Telemetry errors

Failures in agent coordination, heartbeat tracking, approval workflows, and event streaming components.

## Common error signatures

- **`ConnectionError`** or **`TimeoutError`** from Redis operations when memory backend is unavailable
- **`KeyError`** when accessing missing signal or heartbeat data in coordination operations
- **`ValueError`** from invalid agent IDs, signal types, or approval request parameters
- **`JSONDecodeError`** when deserializing malformed coordination signals or heartbeat data
- **`TypeError`** from incorrect payload types in `CoordinationSignal.from_dict()` or `ApprovalRequest.from_dict()`

## Where errors originate

Most telemetry errors stem from these coordination and tracking operations:

- **`CoordinationSignals.signal()`** and **`broadcast()`** — Signal creation failures due to invalid agent IDs or Redis connection issues
- **`HeartbeatCoordinator.start_heartbeat()`** and **`beat()`** — Heartbeat registration problems from missing agent metadata or Redis TTL key conflicts
- **`ApprovalGate.request_approval()`** — Approval workflow errors when timeout values are invalid or context data is malformed
- **`EventStreamer.publish_event()`** and **`consume_events()`** — Stream publishing failures from Redis Stream capacity limits or invalid event data
- **CLI command functions** (`cmd_telemetry_show`, `cmd_agent_performance`, etc.) — Data retrieval errors when telemetry backends are misconfigured

## How to diagnose

1. **Check Redis connectivity first.** Most telemetry components depend on Redis for coordination signals, heartbeats, and event streaming. Verify the memory backend is accessible and responsive.

2. **Validate agent identification.** Many errors stem from inconsistent or missing agent IDs. Check that `agent_id` parameters match active heartbeat registrations and that coordination signals reference valid source/target agents.

3. **Inspect TTL and timeout values.** Coordination signals use 60-second TTLs by default, and heartbeats expire if not refreshed. Look for timing-related failures when agents don't update their status within expected intervals.

4. **Examine payload serialization.** Coordination signals and approval requests serialize context data as JSON. Parse errors indicate malformed dictionaries or non-serializable objects in payload fields.

5. **Monitor approval request lifecycle.** Approval gates transition through pending → approved/denied states with timeout enforcement. Check that approval responses match active request IDs and that expired requests are properly cleaned up.

## Source files

- `src/attune/telemetry/**`

**Tags:** `telemetry`, `metrics`
