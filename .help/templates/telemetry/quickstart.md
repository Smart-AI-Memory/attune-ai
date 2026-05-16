---
type: quickstart
name: telemetry-quickstart
feature: telemetry
depth: quickstart
generated_at: 2026-05-16T06:19:45.848710+00:00
source_hash: ed8485991002cc1c218f67b4f33f230bcbdc4325599a2e03f2bbe584d94a5e90
status: generated
---

# Quickstart: Telemetry

Run the telemetry CLI to see recent usage data and cost savings from your Attune AI setup.

```bash
python -m attune.telemetry show
```

You should see a table of recent telemetry entries logged to `help_queries.jsonl`.

## Prerequisites

- The project is cloned and installed locally
- Redis is accessible (required for heartbeat and coordination features)

## Step 1: View recent telemetry entries

```python
from attune.telemetry import UsageTracker

tracker = UsageTracker()
tracker.show()
```

This prints the most recent entries from the telemetry log.

## Step 2: Check cost savings

```python
from attune.telemetry import UsageTracker

tracker = UsageTracker()
tracker.savings()
```

Expected output: a summary of cost savings from Sonnet → Opus fallback decisions and prompt cache hits.

## Step 3: Monitor agent heartbeats

```python
from attune.telemetry import HeartbeatCoordinator

coordinator = HeartbeatCoordinator()
active = coordinator.get_active_agents()

for agent in active:
    print(agent.agent_id, agent.status, agent.progress)
```

Expected output: one line per active agent showing its ID, current status (`running`, `completed`, etc.), and progress as a float between `0.0` and `1.0`. An empty list means no agents are currently registered.

## Step 4: Request a human approval gate

```python
from attune.telemetry import ApprovalGate

gate = ApprovalGate(agent_id="my-agent")
response = gate.request_approval(
    approval_type="deploy",
    context={"target": "production"},
    timeout=120.0,
)

print(response.approved, response.reason)
```

Expected output: `True <reason>` once a human calls `gate.respond_to_approval(...)`, or a timeout response after 120 seconds.

## What you just did

- Ran the telemetry CLI to confirm the log is populated
- Queried usage data and cost savings
- Listed active agents via `HeartbeatCoordinator`
- Opened a human approval gate with `ApprovalGate`

Next: read the telemetry concept page — say **"what is Attune telemetry?"** — to understand how `UsageTracker`, `HeartbeatCoordinator`, `CoordinationSignals`, and `ApprovalGate` fit together in a multi-agent workflow.
