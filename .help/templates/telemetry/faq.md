---
type: faq
feature: telemetry
depth: faq
generated_at: 2026-04-20T01:24:45.532404+00:00
source_hash: 6acf95560dfe49824641ad827861534eaea26c9226d58caa5c047e5a5c955c0d
status: generated
---

# Telemetry FAQ

## What is telemetry?

Telemetry tracks how Attune AI agents perform, coordinate with each other, and use resources. It provides usage metrics, cost analysis, and quality feedback loops.

## When should I use telemetry?

You need telemetry when you're monitoring agent performance, tracking costs, analyzing model usage patterns, or setting up approval workflows for automated tasks.

## How do I view telemetry data?

Use the telemetry CLI commands:
- `python -m attune.telemetry show` — recent telemetry entries
- `python -m attune.telemetry savings` — cost savings analysis
- `python -m attune.telemetry cache-stats` — prompt caching performance
- `python -m attune.telemetry agent-performance` — agent metrics

## Can agents coordinate with each other?

Yes. Use `CoordinationSignals` to send TTL-based messages between agents, `HeartbeatCoordinator` to track which agents are active, and `ApprovalGate` to require human approval for specific actions.

## How do I track agent status?

Start a heartbeat when your agent begins work:
```python
coordinator = HeartbeatCoordinator()
coordinator.start_heartbeat("my-agent", {"task": "processing"})
coordinator.beat(status="running", progress=0.5)
```

## What's the difference between signals and heartbeats?

Signals are one-time messages between agents with TTL expiration. Heartbeats are continuous status updates that show an agent is alive and working. Use signals for coordination, heartbeats for monitoring.

## How do I set up human approval gates?

Create an approval request that blocks execution until a human responds:
```python
gate = ApprovalGate()
response = gate.request_approval("deploy", {"target": "production"})
if response.approved:
    # proceed with action
```

## Where are the telemetry files?

All telemetry code is in `src/attune/telemetry/`. The CLI entry point is `__main__.py`, coordination classes are in separate modules by function.

**Tags:** `telemetry`, `metrics`
