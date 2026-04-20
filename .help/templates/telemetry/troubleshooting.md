---
type: troubleshooting
feature: telemetry
depth: troubleshooting
generated_at: 2026-04-20T01:24:23.799440+00:00
source_hash: 6acf95560dfe49824641ad827861534eaea26c9226d58caa5c047e5a5c955c0d
status: generated
---

# Troubleshoot telemetry

## Before you start

The telemetry system tracks usage, coordinates agents, manages heartbeats, and provides approval gates. Issues typically manifest as missing data, agent coordination failures, or blocked approval workflows.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Telemetry commands fail with exceptions | Run with `--verbose` and check the Python traceback for the exact failure point |
| Agent coordination signals not received | Verify Redis connection and check if TTL has expired using `CoordinationSignals.get_pending_signals()` |
| Heartbeat tracking shows stale agents | Check Redis TTL keys and network connectivity between agents and Redis |
| Approval requests timeout | Verify the `ApprovalGate` timeout settings and check for pending requests with `get_pending_approvals()` |
| Event streaming stops working | Check Redis Stream health with `EventStreamer.get_stream_info()` |
| Cost savings calculations are wrong | Verify prompt caching is enabled and check token counting in telemetry logs |

## Step-by-step diagnosis

1. **Test the telemetry CLI directly.**
   Run `python -m attune.telemetry --help` to confirm the module loads. Then try specific commands:
   ```bash
   python -m attune.telemetry telemetry-show
   python -m attune.telemetry test-status
   ```

2. **Check Redis connectivity.**
   Most telemetry features depend on Redis for coordination, heartbeats, and events. Test the connection:
   ```python
   from attune.memory import get_redis_client
   redis = get_redis_client()
   redis.ping()  # Should return True
   ```

3. **Examine coordination signals.**
   If agent coordination fails, check for pending signals and TTL expiration:
   ```python
   from attune.telemetry import CoordinationSignals
   signals = CoordinationSignals()
   pending = signals.get_pending_signals()
   print(f"Pending signals: {len(pending)}")
   ```

4. **Verify heartbeat timing.**
   For stale agent issues, check the heartbeat coordinator:
   ```python
   from attune.telemetry import HeartbeatCoordinator
   hb = HeartbeatCoordinator()
   stale = hb.get_stale_agents(threshold_seconds=60)
   print(f"Stale agents: {[a.agent_id for a in stale]}")
   ```

5. **Review event streaming.**
   If events aren't flowing, check stream status:
   ```python
   from attune.telemetry import EventStreamer
   streamer = EventStreamer()
   info = streamer.get_stream_info("coordination")
   print(f"Stream length: {info.get('length', 'unknown')}")
   ```

## Common fixes

- **Redis connection timeout.** Increase the Redis timeout in your configuration or check network connectivity between the client and Redis server.

- **Expired TTL signals.** If coordination signals disappear too quickly, increase `ttl_seconds` when calling `CoordinationSignals.signal()`:
  ```python
  signals.signal("task_complete", ttl_seconds=300)  # 5 minutes instead of default 60
  ```

- **Stale agent cleanup.** Remove dead heartbeat entries:
  ```python
  hb = HeartbeatCoordinator()
  hb.clear_expired_requests()
  ```

- **Approval timeout.** Increase timeout for long-running approval workflows:
  ```python
  gate = ApprovalGate()
  response = gate.request_approval("deploy", context, timeout=300.0)  # 5 minutes
  ```

- **Stream memory usage.** Trim old events to prevent Redis memory issues:
  ```python
  streamer = EventStreamer()
  streamer.trim_stream("coordination", max_length=1000)
  ```

- **Missing telemetry data.** Enable streaming when initializing components:
  ```python
  signals = CoordinationSignals(enable_streaming=True)
  hb = HeartbeatCoordinator(enable_streaming=True)
  ```

## Source files

- `src/attune/telemetry/__main__.py` — CLI entry point
- `src/attune/telemetry/coordination.py` — Agent coordination signals
- `src/attune/telemetry/heartbeat.py` — Agent heartbeat tracking
- `src/attune/telemetry/approval.py` — Human approval gates
- `src/attune/telemetry/streaming.py` — Event streaming
- `src/attune/telemetry/cli_*.py` — CLI command implementations
