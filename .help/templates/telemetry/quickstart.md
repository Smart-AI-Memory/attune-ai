---
type: quickstart
feature: telemetry
depth: quickstart
generated_at: 2026-04-14T15:21:34.809749+00:00
source_hash: 295e5e35ecdbf0e851c8b1779b79738f03b705495583edbf2e6416bf4fe17480
status: generated
---

# Quickstart: telemetry

Track agent heartbeats and view telemetry data in under 5 minutes.

```python
from attune.telemetry import HeartbeatCoordinator

# Start tracking an agent's activity
coordinator = HeartbeatCoordinator()
coordinator.start_heartbeat("my-agent", metadata={"task": "data-processing"})
coordinator.beat(status="running", progress=0.5, current_task="processing files")

# View active agents
active_agents = coordinator.get_active_agents()
print(f"Active agents: {[agent.agent_id for agent in active_agents]}")
```

Expected output:
```
Active agents: ['my-agent']
```

## View telemetry reports

Run the CLI to see comprehensive telemetry data:

```bash
python -m attune.telemetry show
```

This displays recent telemetry entries including agent activity, performance metrics, and cost savings from model fallbacks.

## Track agent coordination

Use coordination signals to enable communication between agents:

```python
from attune.telemetry import CoordinationSignals

signals = CoordinationSignals(agent_id="agent-1")
signal_id = signals.broadcast("task-complete", payload={"result": "success"})

# Other agents can wait for this signal
received = signals.wait_for_signal("task-complete", timeout=10.0)
print(f"Received signal: {received.payload}")
```

**Next:** Set up human approval gates with `ApprovalGate` to add workflow control to your agent systems.
