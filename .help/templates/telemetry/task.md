---
type: task
feature: telemetry
depth: task
generated_at: 2026-05-04T02:37:27.827841+00:00
source_hash: ed8485991002cc1c218f67b4f33f230bcbdc4325599a2e03f2bbe584d94a5e90
status: generated
---

# Work with telemetry

Use telemetry when you need to track agent coordination, monitor performance metrics, or implement human approval workflows in Attune AI.

## Prerequisites

- Access to the project source code
- Familiarity with the telemetry module at `src/attune/telemetry/`
- Basic understanding of Redis for data persistence

## Configure telemetry components

1. **Set up coordination signals between agents.**
   Use `CoordinationSignals` to send TTL-based messages between agents:
   ```python
   from attune.telemetry import CoordinationSignals

   coordinator = CoordinationSignals(agent_id="my_agent")
   signal_id = coordinator.signal("task_complete", payload={"result": "success"})
   ```

2. **Initialize heartbeat monitoring.**
   Use `HeartbeatCoordinator` to track agent health and progress:
   ```python
   from attune.telemetry import HeartbeatCoordinator

   heartbeat = HeartbeatCoordinator()
   heartbeat.start_heartbeat("agent_1", metadata={"task": "data_processing"})
   heartbeat.beat(status="running", progress=0.5, current_task="processing file 2/4")
   ```

3. **Configure human approval gates.**
   Use `ApprovalGate` for workflow control requiring human decisions:
   ```python
   from attune.telemetry import ApprovalGate

   gate = ApprovalGate(agent_id="workflow_agent")
   response = gate.request_approval("deploy", context={"env": "production"})
   ```

4. **Set up event streaming.**
   Use `EventStreamer` for real-time event monitoring:
   ```python
   from attune.telemetry import EventStreamer

   streamer = EventStreamer()
   event_id = streamer.publish_event("task_started", {"agent": "worker_1"})
   ```

## Run telemetry commands

1. **Check cost savings from model fallbacks.**
   Run: `python -m attune.telemetry sonnet-opus-analysis`

2. **View agent performance metrics.**
   Run: `python -m attune.telemetry agent-performance`

3. **Monitor test execution status.**
   Run: `python -m attune.telemetry test-status`

4. **Review Tier 1 automation status.**
   Run: `python -m attune.telemetry tier1-status`

5. **Generate task routing reports.**
   Run: `python -m attune.telemetry task-routing-report`

## Verify telemetry is working

Check that your telemetry setup is functioning correctly:

1. **Confirm agents are visible.**
   Run `python -m attune.telemetry agent-performance` and verify your agent appears in the active list.

2. **Test signal delivery.**
   Send a test signal and verify it's received within the TTL window.

3. **Validate approval workflow.**
   Submit a test approval request and confirm it appears in pending approvals.

Success indicators:
- Agents report heartbeats without Redis connection errors
- Coordination signals are delivered within their TTL period
- Approval requests persist until responded to or expired
- Event streams contain expected event types with valid timestamps
