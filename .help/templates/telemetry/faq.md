---
type: faq
name: telemetry-faq
feature: telemetry
depth: faq
generated_at: 2026-05-16T06:19:45.846271+00:00
source_hash: ed8485991002cc1c218f67b4f33f230bcbdc4325599a2e03f2bbe584d94a5e90
status: generated
---

# Telemetry FAQ

## What does the telemetry feature do?

It tracks usage, coordinates agents via TTL-based signals, monitors agent heartbeats, gates workflows on human approval, and streams real-time events through Redis Streams. It also records feedback and calculates cost savings from model-tier routing.

## What can I track with telemetry?

You can track agent status and progress with `HeartbeatCoordinator`, send and receive inter-agent coordination signals with `CoordinationSignals`, stream and consume real-time events with `EventStreamer`, and collect human approval decisions with `ApprovalGate`.

## How do I start the telemetry CLI?

Call `main()` from `src/attune/telemetry/__main__.py`, or run the module directly with `python -m attune.telemetry`. From there you can run subcommands like `cmd_telemetry_show()` to view recent entries, `cmd_telemetry_savings()` to see cost savings, and `cmd_telemetry_cache_stats()` to check prompt-caching performance.

## What is a coordination signal and how long does it live?

A `CoordinationSignal` is a typed message sent from one agent to another (or broadcast to all agents). Its default TTL is 60 seconds. You can override that per signal using the `ttl_seconds` parameter on `CoordinationSignals.signal()` or `CoordinationSignals.broadcast()`.

## How do I check whether an agent is still running?

Call `HeartbeatCoordinator.is_agent_alive(agent_id)`. To get full status, use `get_agent_status(agent_id)`, which returns an `AgentHeartbeat` with fields for `status`, `progress`, and `current_task`. To find agents that haven't sent a heartbeat recently, call `get_stale_agents(threshold_seconds=60.0)`.

## How does human approval gating work?

Your agent calls `ApprovalGate.request_approval()` with an `approval_type` and optional context dict. The call blocks until a human responds via `respond_to_approval()` or the request times out. The response is an `ApprovalResponse` with `approved`, `responder`, and an optional `reason`.

## What happens to approval requests that time out?

They remain in storage with `status = 'pending'` until you explicitly remove them. Call `ApprovalGate.clear_expired_requests()` to purge them.

## How do I consume events from the stream?

Use `EventStreamer.consume_events()`, optionally filtering by a list of `event_types`. To look back at past events rather than waiting for new ones, call `get_recent_events(event_type, count=100)` instead.

## Where is telemetry data stored by default?

Help queries are logged to `help_queries.jsonl` (the value of `_DEFAULT_FILE`). Coordination signals and heartbeats use Redis TTL keys. Event streams are backed by Redis Streams.

## How do I debug a telemetry problem?

Run `pytest -k "telemetry" -v` first. If tests pass but your code still fails, enable debug logging and add a `logger.debug` statement at the suspected failure point. For symptom-based diagnosis, see the troubleshooting page for this feature.

## Where are the source files?

All telemetry source files live under `src/attune/telemetry/`.

**Tags:** `telemetry`, `metrics`
