---
type: comparison
name: telemetry-comparison
feature: telemetry
depth: comparison
generated_at: 2026-05-16T06:19:45.856170+00:00
source_hash: ed8485991002cc1c218f67b4f33f230bcbdc4325599a2e03f2bbe584d94a5e90
status: generated
---

# Comparison: Telemetry vs alternatives

## Context

The telemetry feature covers four distinct concerns that can each be addressed by different mechanisms: usage tracking, agent coordination, agent liveness monitoring, and human approval gating. This page helps you decide which telemetry subsystem — or alternative approach — fits your situation.

## Feature breakdown

| Capability | Telemetry subsystem | What it gives you | What it does not do |
|---|---|---|---|
| **Usage tracking** | `UsageTracker` / `FeedbackLoop` | Logs queries to `help_queries.jsonl`; computes per-template confidence scores via `good/(good+bad)` | Does not expose real-time streams; data is append-only JSONL |
| **Agent coordination** | `CoordinationSignals` | TTL-based signals between named agents; targeted (`signal()`) or broadcast (`broadcast()`); blocking wait (`wait_for_signal()`) with configurable timeout | Signals expire after `ttl_seconds` (default 60 s); no delivery guarantee after TTL lapses |
| **Agent liveness** | `HeartbeatCoordinator` | Tracks `status`, `progress`, and `current_task` per agent; detects stale agents beyond a configurable threshold (default 60 s) | Does not restart failed agents; detection only |
| **Human approval gates** | `ApprovalGate` | Pauses workflow execution until a human calls `respond_to_approval()`; supports per-request timeouts | Synchronous blocking call — unsuitable for fire-and-forget workflows |
| **Real-time event streaming** | `EventStreamer` | Publishes and consumes typed events via Redis Streams; supports backfill via `get_recent_events()` | Requires Redis; not a replacement for structured logging |
| **CLI analysis** | `cmd_sonnet_opus_analysis()`, `cmd_tier1_status()`, `cmd_task_routing_report()`, etc. | Pre-built reports for cost savings, Tier 1 automation status, task routing, and test status | Read-only reporting; does not mutate state |

## When to use telemetry

Choose a telemetry subsystem when your work maps directly to one of the following:

- **Template quality feedback** — You want to accumulate `good`/`bad` ratings and surface confidence scores that influence template ranking. Use `record_template_feedback()` and `get_template_confidence()`, or the CLI: `attune help-docs <id> --feedback good|bad`.
- **Multi-agent coordination** — Two or more agents need to hand off work or wait on each other. `CoordinationSignals.signal()` sends to a specific agent; `CoordinationSignals.broadcast()` fans out to all listeners. TTL ensures stale signals self-clean.
- **Agent health monitoring** — You need to know which agents are alive and what they are doing. `HeartbeatCoordinator.get_active_agents()` and `get_stale_agents(threshold_seconds=…)` answer both questions without polling custom state.
- **Approval-gated workflows** — A workflow step must not proceed without an explicit human `approved: true` response. `ApprovalGate.request_approval()` blocks until a response arrives or the timeout expires.
- **Operational reporting** — You need a snapshot of cost savings, test coverage by file, or task routing decisions. Run the appropriate CLI subcommand (`cmd_sonnet_opus_analysis`, `cmd_file_test_status`, etc.) rather than parsing raw logs yourself.

## When not to use telemetry

- **Cross-feature orchestration** — If your logic needs to coordinate telemetry with other top-level features, use the orchestration layer above `src/attune/telemetry/` rather than wiring subsystems together directly.
- **Ephemeral scripts** — Setting up `HeartbeatCoordinator` or `CoordinationSignals` for a one-off script adds overhead with no payoff. A simple log statement is sufficient for throwaway work.
- **Guaranteed message delivery** — `CoordinationSignals` uses Redis TTL keys. If an agent is offline when a signal arrives and the TTL lapses, the signal is gone. If you need durable queuing, look outside this module.
- **Agent remediation** — `HeartbeatCoordinator` tells you an agent is stale; it does not restart or reschedule it. Pair it with an external supervisor if you need automatic recovery.
- **Replacing structured logging** — `EventStreamer` is designed for real-time coordination events, not audit trails. Do not use it as a general-purpose logger.

## Decision rules

| Situation | Use this |
|---|---|
| Rating a help template and influencing its ranking | `FeedbackLoop` / `record_template_feedback()` |
| One agent needs to wake another agent | `CoordinationSignals.signal()` |
| One agent needs to notify all agents | `CoordinationSignals.broadcast()` |
| Checking whether a specific agent is still running | `HeartbeatCoordinator.is_agent_alive()` |
| Finding all agents that have gone silent | `HeartbeatCoordinator.get_stale_agents()` |
| Pausing a workflow for human sign-off | `ApprovalGate.request_approval()` |
| Viewing cost or routing reports without writing code | `attune telemetry <subcommand>` CLI |
| Durable, guaranteed message delivery between agents | Look outside `src/attune/telemetry/` |

## Source files

- `src/attune/telemetry/**`

**Tags:** `telemetry`, `metrics`
