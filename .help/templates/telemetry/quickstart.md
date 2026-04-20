---
type: quickstart
feature: telemetry
depth: quickstart
generated_at: 2026-04-20T01:24:58.686164+00:00
source_hash: 6acf95560dfe49824641ad827861534eaea26c9226d58caa5c047e5a5c955c0d
status: generated
---

# Quickstart: View Telemetry Status

Check your system's telemetry data and cost savings in under 5 minutes.

```bash
python -m attune.telemetry show
```

Expected output:
```
Recent Telemetry Entries (last 10):
2024-04-20 01:15:23 | agent_task | success | model=claude-3-sonnet | cost=$0.0045
2024-04-20 01:14:18 | test_run   | success | tests_passed=23      | cost=$0.0023
...

Total entries: 147
```

## Step 1: View cost savings

```bash
python -m attune.telemetry savings
```

This shows how much you've saved through model tier optimization and prompt caching.

## Step 2: Check agent coordination

```python
from attune.telemetry import HeartbeatCoordinator

coordinator = HeartbeatCoordinator()
active_agents = coordinator.get_active_agents()
print(f"Active agents: {len(active_agents)}")
```

Expected output shows running agents with their current tasks and progress.

## Step 3: Send a coordination signal

```python
from attune.telemetry import CoordinationSignals

signals = CoordinationSignals()
signal_id = signals.broadcast("task_complete", payload={"result": "success"})
print(f"Signal sent: {signal_id}")
```

This broadcasts a message to all listening agents.

## What you just did

- Viewed your telemetry history and cost data
- Checked which agents are currently active
- Sent a coordination signal between agents

The telemetry system tracks usage, coordinates agents via TTL signals, monitors heartbeats, and manages human approval gates for workflow control.

## Next

Run `python -m attune.telemetry tier1-status` to see comprehensive automation status across all your workflows.
