---
type: troubleshooting
name: telemetry-troubleshooting
feature: telemetry
depth: troubleshooting
generated_at: 2026-05-16T06:19:45.843807+00:00
source_hash: ed8485991002cc1c218f67b4f33f230bcbdc4325599a2e03f2bbe584d94a5e90
status: generated
---

# Troubleshoot telemetry

## Before you start

Attune's telemetry subsystem covers usage tracking, feedback loops, agent heartbeats, inter-agent coordination signals, human approval gates, and real-time event streaming. Symptoms can originate in any of these areas. Identify which component is affected before diving into code.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `attune telemetry` command exits with a traceback | Read the exception type and line number — most CLI failures surface in `main()` in `src/attune/telemetry/__main__.py` |
| Cost-savings or cache-stats output is missing or wrong | Run `cmd_telemetry_savings()` and `cmd_telemetry_cache_stats()` directly and compare against raw entries from `cmd_telemetry_show()` |
| Sonnet→Opus fallback analysis shows no data | Confirm telemetry entries exist: `attune telemetry show`; if the log is empty, check that `help_queries.jsonl` is being written |
| An agent appears stuck or unresponsive | Call `HeartbeatCoordinator.get_stale_agents(threshold_seconds=60.0)` — any agent listed there has not called `beat()` within the TTL |
| An agent shows `is_agent_alive()` returning `False` unexpectedly | Check that the agent's loop is calling `beat()` and that its `HeartbeatCoordinator` is connected to the same Redis memory instance |
| A coordination signal is never received | Call `CoordinationSignals.get_pending_signals()` to see what is queued; verify `ttl_seconds` has not expired before `wait_for_signal()` polls |
| An approval request times out without a response | Call `ApprovalGate.get_pending_approvals()` to confirm the request exists; check `timeout_seconds` on the `ApprovalRequest` and whether `clear_expired_requests()` already removed it |
| Event stream consumers receive no events | Call `EventStreamer.get_stream_info(event_type)` to verify the stream exists and has entries; confirm `start_id` in `consume_events()` is not set past the last entry |
| Intermittent signal or heartbeat loss | Check for Redis TTL expiry — `CoordinationSignal.ttl_seconds` defaults to 60 and `get_stale_agents()` uses a 60-second threshold; reduce poll intervals or increase TTLs |

## Diagnosis steps

Follow these steps in order — each one is cheaper than the next.

1. **Reproduce the failure with a minimal call.**
   Strip the failing call down to its required arguments and run it outside the surrounding workflow. For CLI commands, run the subcommand directly:

   ```
   attune telemetry show
   attune telemetry cache-stats
   attune telemetry savings
   ```

   Confirm the failure occurs before adding complexity.

2. **Check the telemetry log file.**
   All CLI commands read from `help_queries.jsonl` (the `_DEFAULT_FILE` constant). Verify the file exists and contains recent entries:

   ```bash
   ls -lh help_queries.jsonl
   tail -5 help_queries.jsonl
   ```

   An empty or missing file explains missing output in `cmd_telemetry_show()`, `cmd_telemetry_savings()`, and `cmd_telemetry_cache_stats()`.

3. **Enable DEBUG logging and re-run.**
   Set the log level before invoking the failing command:

   ```bash
   ATTUNE_LOG_LEVEL=DEBUG attune telemetry show
   ```

   Look for Redis connection errors, missing keys, or unexpected `None` returns from heartbeat or signal lookups.

4. **Inspect the relevant entry point.**
   Match your symptom to the function responsible:

   - `main()` — CLI argument parsing and subcommand dispatch
   - `cmd_telemetry_show()` — recent telemetry entries
   - `cmd_telemetry_savings()` — cost-savings calculation
   - `cmd_telemetry_cache_stats()` — prompt caching statistics
   - `cmd_sonnet_opus_analysis()` — Sonnet 4.5 → Opus 4.5 fallback analysis
   - `cmd_file_test_status()` / `cmd_test_status()` — per-file and overall test status
   - `cmd_tier1_status()` / `cmd_task_routing_report()` — Tier 1 automation and task routing

   Add a temporary `print()` or log statement at the function's first line to confirm it is being reached.

5. **Run the telemetry test suite.**

   ```bash
   pytest -k "telemetry" -v
   ```

   A failing test that exercises the broken path gives you a reproducible baseline and a fixture you can reuse when writing a fix.

## Common fixes

**Empty or missing `help_queries.jsonl`**
The file is not created automatically if no queries have been recorded. Trigger a help query to initialize it, or create the file manually and verify its path matches `_DEFAULT_FILE`.

**Heartbeat agent shows as stale immediately**
The agent is not calling `beat()` frequently enough relative to the TTL. Either increase `ttl_seconds` when calling `start_heartbeat()`, or call `beat()` more frequently inside the agent loop:

```python
coordinator.beat(status='running', progress=0.5, current_task='processing')
```

**Coordination signal expires before it is consumed**
Increase `ttl_seconds` when sending the signal, or reduce `poll_interval` in `wait_for_signal()`:

```python
signals.signal(signal_type='ready', ttl_seconds=120)
signals.wait_for_signal('ready', timeout=90.0, poll_interval=0.25)
```

**Approval request disappears before a human responds**
`clear_expired_requests()` removes requests whose `timeout_seconds` has elapsed. Increase `timeout` when calling `request_approval()`, or call `get_pending_approvals()` immediately after to confirm the request was stored.

**Event stream consumer receives nothing**
The default `start_id='$'` in `consume_events()` means "events from now onward." To read existing events, use `get_recent_events()` instead:

```python
events = streamer.get_recent_events(event_type='my_event', count=50)
```

**Redis connection errors across all components**
`HeartbeatCoordinator`, `CoordinationSignals`, `ApprovalGate`, and `EventStreamer` all accept a `memory` argument. If you pass `None`, each class uses its default connection. Confirm all components in the same workflow share the same Redis instance and that the connection is reachable.

**Dependency version mismatch**
A Redis client upgrade can change serialization behavior. Run:

```bash
pip show redis
```

and confirm the installed version is compatible with the version specified in your project's dependency file.

## Source files

- `src/attune/telemetry/**`

**Tags:** `telemetry`, `metrics`
