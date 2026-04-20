---
type: concept
feature: telemetry
depth: concept
generated_at: 2026-04-20T01:22:40.975305+00:00
source_hash: 6acf95560dfe49824641ad827861534eaea26c9226d58caa5c047e5a5c955c0d
status: generated
---

# Telemetry

Telemetry tracks how Attune AI agents coordinate, perform, and handle human approval workflows across 16 monitoring modules.

## What telemetry covers

Attune's telemetry system monitors three distinct operational layers:

**Agent coordination** — Agents send TTL-based signals to coordinate work and avoid conflicts. When one agent claims a task, others receive coordination signals and back off. These signals expire automatically to prevent deadlocks.

**Performance tracking** — Each active agent sends heartbeat signals that include status, progress percentage, and current task. The system detects stale agents when heartbeats stop arriving and can trigger recovery workflows.

**Human approval gates** — For sensitive operations like code changes or file deletions, agents pause and request human approval. The approval system queues these requests with context and timeouts, then routes responses back to the waiting agent.

## Core coordination components

| Component | Responsibility | Example use |
|-----------|---------------|-------------|
| `CoordinationSignals` | TTL-based agent messaging | Agent A signals "claimed file X" so Agent B skips it |
| `HeartbeatCoordinator` | Track agent health and progress | Monitor 5 agents processing test files, detect if one crashes |
| `ApprovalGate` | Human decision checkpoints | Request approval before deleting old migration files |
| `EventStreamer` | Real-time event broadcasting | Publish "test completed" events to Redis streams |

## Data flow between agents

Agents use Redis as a coordination layer with three data patterns:

1. **Signals** — Temporary messages with TTL expiration (`agent-123-claimed-file-x` expires in 60 seconds)
2. **Heartbeats** — Regular status updates (`agent-123-status` contains current progress and task)
3. **Approval queues** — Pending human decisions (`approval-delete-files-request-456` waits for response)

The telemetry CLI provides visibility into these flows with commands like `attn telemetry agent-performance` and `attn telemetry test-status`.

## Operational insights

The telemetry system tracks cost savings from prompt caching, model tier routing (Sonnet 4.5 to Opus 4.5 fallbacks), and test execution patterns. It identifies which agents handle which file types most efficiently and surfaces performance bottlenecks in the coordination layer.
