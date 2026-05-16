---
type: error
name: telemetry-error
feature: telemetry
depth: error
generated_at: 2026-05-16T06:19:45.835768+00:00
source_hash: ed8485991002cc1c218f67b4f33f230bcbdc4325599a2e03f2bbe584d94a5e90
status: generated
---

# Telemetry errors

## Common error signatures

Telemetry errors typically fall into three categories: failures in CLI command execution, failures in agent coordination and heartbeat tracking, and failures in approval gate or event streaming operations.

- **CLI commands returning non-zero** — `main()` and subcommands such as `cmd_telemetry_show()`, `cmd_telemetry_savings()`, and `cmd_telemetry_cache_stats()` all return `int` exit codes. A return value other than `0` indicates a failure in data retrieval or rendering.
- **`KeyError` or `ValueError` in `CoordinationSignal.from_dict()` or `AgentHeartbeat.from_dict()`** — these dataclass deserializers expect specific keys (`signal_id`, `signal_type`, `source_agent`, `agent_id`, `status`, `progress`, etc.). Missing or mistyped fields raise these exceptions when parsing stored Redis data.
- **`TimeoutError` or `None` return from `CoordinationSignals.wait_for_signal()`** — the method polls for up to `timeout` seconds (default `30.0`) and returns `None` if no matching signal arrives. Callers that don't handle `None` may propagate `AttributeError` or silent no-ops downstream.
- **Stale or missing heartbeat** — `HeartbeatCoordinator.is_agent_alive()` returns `False` when the TTL key has expired in Redis. If your workflow assumes an agent is running, this produces incorrect branching rather than a raised exception, making it easy to miss.
- **`ApprovalGate.request_approval()` timing out** — if no human responds within `timeout_seconds`, the gate returns an `ApprovalResponse` with `approved=False`. Workflows that don't check `response.approved` before proceeding will act on a rejected or timed-out request.
- **`EventStreamer` publish/consume failures** — `publish_event()` and `consume_events()` depend on a live Redis Streams connection. A connection error here produces an exception that propagates to the caller with no automatic retry.

## Where errors originate

The following CLI entry points are the most common raise sites. Failures in the underlying coordination and streaming classes typically bubble up through these commands.

- `main()` — top-level telemetry CLI dispatcher; catches unhandled exceptions from all subcommands.
- `cmd_sonnet_opus_analysis()` — reads Sonnet 4.5 → Opus 4.5 fallback data; fails if the underlying telemetry log is missing or malformed.
- `cmd_file_test_status()` and `cmd_test_status()` — query per-file and aggregate test status; fail if the telemetry store is unavailable.
- `cmd_tier1_status()` and `cmd_task_routing_report()` — aggregate automation metrics; sensitive to incomplete or corrupt telemetry records.
- `cmd_agent_performance()`, `cmd_telemetry_savings()`, `cmd_telemetry_cache_stats()` — all read from the telemetry log (`help_queries.jsonl` by default at `_DEFAULT_FILE`); fail if that file is absent or written in an incompatible format (log version `_LOG_VERSION = '1.0'`).

## How to diagnose

1. **Check the CLI exit code first.** All telemetry subcommands return `0` on success. Any other value means a command-specific failure occurred — run the command directly in your shell to see the error output before it gets swallowed by a calling script.

2. **Inspect `help_queries.jsonl` for format issues.** The default telemetry log is a JSONL file. If a line is malformed or written by a different log version than `1.0`, deserialization in `from_dict()` will raise `KeyError` or `ValueError`. Open the file and check that each line is valid JSON containing the expected fields.

3. **Verify Redis connectivity for coordination and streaming failures.** `CoordinationSignals`, `HeartbeatCoordinator`, `ApprovalGate`, and `EventStreamer` all depend on a `memory` backend (Redis). If the backend is unavailable, every method that reads or writes signals will fail. Confirm the Redis connection before debugging the telemetry logic itself.

4. **Check TTL expiry for `None` returns from `wait_for_signal()` and `is_agent_alive()`.** These methods return `None` or `False` — not exceptions — when a TTL key has expired. If your workflow is silently skipping a coordination step, check whether the `ttl_seconds` on the relevant `CoordinationSignal` (default `60`) is too short for your workload, and whether `get_stale_agents(threshold_seconds=60.0)` reports the affected agent.

5. **Audit approval responses before acting on them.** When `ApprovalGate.request_approval()` returns, check `response.approved` explicitly. A `False` value can mean either a rejection or a timeout — `response.reason` and `response.responder` distinguish between the two.

6. **Enable `DEBUG` logging.** Most telemetry classes use `logging`. Set the log level to `DEBUG` and re-run the failing scenario. Logged state leading up to the failure usually identifies whether the root cause is a missing key, an expired TTL, or a backend connection error.

## Source files

- `src/attune/telemetry/**`

**Tags:** `telemetry`, `metrics`
