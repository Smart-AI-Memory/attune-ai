---
type: faq
feature: telemetry
depth: faq
generated_at: 2026-04-14T15:21:25.145052+00:00
source_hash: 295e5e35ecdbf0e851c8b1779b79738f03b705495583edbf2e6416bf4fe17480
status: generated
---

# Telemetry FAQ

## What is telemetry?

Telemetry provides usage tracking, agent coordination, and workflow control for Attune AI systems.

## What can I do with telemetry?

You can track agent performance, coordinate multiple agents using TTL signals, monitor heartbeats, set up human approval gates, and stream real-time events.

## How do I coordinate agents?

Use `CoordinationSignals` to send TTL-based signals between agents. Call `signal()` to send to a specific agent or `broadcast()` to send to all agents.

## How do I track agent health?

Use `HeartbeatCoordinator`. Call `start_heartbeat()` when your agent begins work, `beat()` periodically to update status, and `stop_heartbeat()` when finished.

## How do I require human approval?

Use `ApprovalGate`. Call `request_approval()` with your approval type and context. The method blocks until a human responds via `respond_to_approval()`.

## How do I stream events in real-time?

Use `EventStreamer`. Call `publish_event()` to send events and `consume_events()` to receive them. Events use Redis Streams for reliable delivery.

## What telemetry reports are available?

Run `python -m attune.telemetry` with subcommands like `test-status`, `agent-performance`, `savings`, or `cache-stats` to see different reports.

## How do I debug telemetry issues?

Run `pytest -k "telemetry" -v` first. If tests pass but your code fails, add `logger.debug` statements and enable logging to trace the issue.

## Where are the source files?

All telemetry code is in `src/attune/telemetry/`.

**Tags:** `telemetry`, `metrics`
