---
type: note
name: telemetry-note
feature: telemetry
depth: note
generated_at: 2026-05-16T06:19:45.853537+00:00
source_hash: ed8485991002cc1c218f67b4f33f230bcbdc4325599a2e03f2bbe584d94a5e90
status: generated
---

# Note: telemetry

## Context

The `attune.telemetry` package covers four distinct concerns that share a common infrastructure layer:

- **Usage tracking** — records help queries to `help_queries.jsonl` (log version `1.0`) and exposes cost and cache statistics via the CLI
- **Agent coordination** — routes TTL-scoped signals between agents through `CoordinationSignals` (backed by Redis)
- **Heartbeat tracking** — lets `HeartbeatCoordinator` detect stale agents using Redis TTL keys
- **Human approval gates** — suspends workflow execution until a human responds via `ApprovalGate`

The feedback loop described in `concepts/feedback-loop.md` (`FeedbackLoop`, `FeedbackEntry`, `QualityStats`) is part of this package and is exported alongside the coordination and tracking classes.

## Design

The package exposes classes and CLI entry points at the same boundary. The CLI functions in `cli_analysis.py` and `cli_automation.py` (for example, `cmd_sonnet_opus_analysis`, `cmd_tier1_status`) operate on the same data structures that the classes produce — `AgentHeartbeat`, `CoordinationSignal`, `ApprovalRequest`, and their counterparts. Neither layer wraps the other; they share the underlying Redis-backed memory store passed at construction time.

`CoordinationSignal` carries a `ttl_seconds` field (default 60) that controls how long a signal remains visible to `wait_for_signal` and `check_signal`. Signals past their TTL are invisible to consumers but are not automatically deleted; `clear_signals()` must be called explicitly to remove them.

## Source

`src/attune/telemetry/**` — 16 source files total.

**Tags:** `telemetry`, `metrics`
