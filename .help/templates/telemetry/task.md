---
type: task
feature: telemetry
depth: task
generated_at: 2026-04-14T15:19:31.160484+00:00
source_hash: 295e5e35ecdbf0e851c8b1779b79738f03b705495583edbf2e6416bf4fe17480
status: generated
---

# Work with telemetry

Use telemetry when you need to track agent performance, coordinate multi-agent workflows, or implement human approval gates in your AI system.

## Prerequisites

- Access to the project source code
- Familiarity with the files under `src/attune/telemetry/`
- Redis connection for coordination signals and heartbeat tracking

## Set up agent coordination

1. **Initialize coordination signals**
   Create a `CoordinationSignals` instance to enable agent-to-agent communication:
   ```python
   from attune.telemetry import CoordinationSignals

   signals = CoordinationSignals(agent_id="my-agent")
   ```

2. **Send signals between agents**
   Use `signal()` for targeted communication or `broadcast()` for all agents:
   ```python
   # Send to specific agent
   signal_id = signals.signal(
       signal_type="task_complete",
       target_agent="worker-agent",
       payload={"result": "success"}
   )

   # Broadcast to all agents
   signals.broadcast(signal_type="shutdown", payload={"reason": "maintenance"})
   ```

3. **Wait for coordination signals**
   Use `wait_for_signal()` to block until receiving expected signals:
   ```python
   response = signals.wait_for_signal(
       signal_type="approval_response",
       timeout=60.0
   )
   ```

## Track agent health with heartbeats

1. **Start heartbeat monitoring**
   Initialize and start sending heartbeats for your agent:
   ```python
   from attune.telemetry import HeartbeatCoordinator

   heartbeat = HeartbeatCoordinator()
   heartbeat.start_heartbeat(
       agent_id="worker-1",
       metadata={"version": "1.2.3"},
       display_name="Data Processor"
   )
   ```

2. **Update agent status regularly**
   Send periodic updates about your agent's current state:
   ```python
   heartbeat.beat(
       status="processing",
       progress=0.75,
       current_task="analyzing dataset"
   )
   ```

3. **Monitor other agents**
   Check which agents are active and their current status:
   ```python
   active_agents = heartbeat.get_active_agents()
   stale_agents = heartbeat.get_stale_agents(threshold_seconds=120)
   ```

## Implement approval gates

1. **Request human approval**
   Pause workflows to wait for human decisions:
   ```python
   from attune.telemetry import ApprovalGate

   gate = ApprovalGate(agent_id="automation-agent")
   response = gate.request_approval(
       approval_type="high_cost_operation",
       context={"estimated_cost": 500, "operation": "bulk_analysis"},
       timeout=300
   )

   if response.approved:
       # Continue with operation
       pass
   ```

2. **Respond to approval requests**
   Provide approval decisions from supervisors or operators:
   ```python
   # Get pending requests
   pending = gate.get_pending_approvals(approval_type="high_cost_operation")

   # Approve or reject
   gate.respond_to_approval(
       request_id=pending[0].request_id,
       approved=True,
       responder="supervisor@company.com",
       reason="Budget approved for Q4 analysis"
   )
   ```

## Stream real-time events

1. **Publish system events**
   Send events to Redis streams for real-time monitoring:
   ```python
   from attune.telemetry import EventStreamer

   streamer = EventStreamer()
   event_id = streamer.publish_event(
       event_type="agent_started",
       data={"agent_id": "worker-1", "capabilities": ["analysis", "reporting"]}
   )
   ```

2. **Consume events in real-time**
   Listen for specific event types:
   ```python
   for event in streamer.consume_events(
       event_types=["agent_started", "task_completed"],
       block_ms=1000
   ):
       print(f"Received {event.event_type}: {event.data}")
   ```

## Run telemetry CLI commands

1. **View telemetry data**
   Use the CLI to inspect system metrics:
   ```bash
   python -m attune.telemetry show
   python -m attune.telemetry savings
   python -m attune.telemetry cache-stats
   ```

2. **Analyze agent performance**
   Generate performance and status reports:
   ```bash
   python -m attune.telemetry agent-performance
   python -m attune.telemetry test-status
   python -m attune.telemetry tier1-status
   ```

## Verify setup

Check that your telemetry integration works correctly:

1. **Confirm signal delivery**: Send a test signal and verify it appears in `get_pending_signals()`
2. **Validate heartbeat tracking**: Start a heartbeat and confirm the agent appears in `get_active_agents()`
3. **Test approval flow**: Create an approval request and verify it appears in `get_pending_approvals()`
4. **Check event streaming**: Publish an event and confirm it's received by a consumer

Your telemetry system is working when agents can coordinate through signals, heartbeats show active agent status, and approval gates properly pause workflows for human decisions.
