---
type: task
feature: telemetry
depth: task
generated_at: 2026-04-20T01:22:58.325000+00:00
source_hash: 6acf95560dfe49824641ad827861534eaea26c9226d58caa5c047e5a5c955c0d
status: generated
---

# Work with telemetry

Use telemetry when you need to track system usage, analyze agent performance, or implement workflow control gates in Attune AI.

## Prerequisites

- Access to the project source code
- Familiarity with Redis (used for coordination signals and heartbeats)
- Understanding of the Attune AI agent architecture

## Configure telemetry components

1. **Choose your telemetry component.**
   The telemetry system has four main areas:
   - **Agent coordination** — Use `CoordinationSignals` for inter-agent communication with TTL-based expiration
   - **Heartbeat monitoring** — Use `HeartbeatCoordinator` to track agent health and progress
   - **Approval workflows** — Use `ApprovalGate` for human approval gates in automated workflows
   - **Event streaming** — Use `EventStreamer` for real-time event publishing via Redis Streams

2. **Import the required classes.**
   Add the imports you need to your module:
   ```python
   from attune.telemetry import CoordinationSignals, HeartbeatCoordinator
   from attune.telemetry import ApprovalGate, EventStreamer
   ```

3. **Initialize with Redis memory.**
   All telemetry classes require a Redis connection:
   ```python
   # For coordination signals
   signals = CoordinationSignals(memory=your_redis_memory, agent_id="your_agent")

   # For heartbeat tracking
   heartbeat = HeartbeatCoordinator(memory=your_redis_memory)

   # For approval gates
   approval = ApprovalGate(memory=your_redis_memory, agent_id="your_agent")
   ```

## Implement agent coordination

1. **Send coordination signals.**
   Use signals for agent-to-agent communication:
   ```python
   # Send to specific agent
   signal_id = signals.signal(
       signal_type="task_complete",
       target_agent="processor_agent",
       payload={"result": "success", "data": results}
   )

   # Broadcast to all agents
   signals.broadcast(
       signal_type="shutdown",
       payload={"reason": "maintenance"}
   )
   ```

2. **Wait for responses.**
   Block until you receive expected signals:
   ```python
   response = signals.wait_for_signal(
       signal_type="ack",
       source_agent="processor_agent",
       timeout=30.0
   )

   if response:
       print(f"Got acknowledgment: {response.payload}")
   ```

## Set up heartbeat monitoring

1. **Start agent heartbeats.**
   Register your agent with the heartbeat system:
   ```python
   heartbeat.start_heartbeat(
       agent_id="my_agent",
       metadata={"version": "1.0", "role": "processor"},
       display_name="File Processor Agent"
   )
   ```

2. **Update progress regularly.**
   Call `beat()` periodically to show the agent is alive:
   ```python
   for i, item in enumerate(work_items):
       heartbeat.beat(
           status="processing",
           progress=(i / len(work_items)) * 100,
           current_task=f"Processing {item}"
       )
       process_item(item)

   heartbeat.stop_heartbeat(final_status="completed")
   ```

3. **Monitor other agents.**
   Check the health of the agent ecosystem:
   ```python
   active_agents = heartbeat.get_active_agents()
   stale_agents = heartbeat.get_stale_agents(threshold_seconds=120)

   for agent in stale_agents:
       print(f"Agent {agent.agent_id} may be stuck: {agent.current_task}")
   ```

## Add approval gates

1. **Request human approval.**
   Pause workflow execution for human decisions:
   ```python
   response = approval.request_approval(
       approval_type="delete_files",
       context={
           "files": file_list,
           "reason": "Cleanup old cache files",
           "impact": "Low - regenerable data"
       },
       timeout=300.0  # 5 minutes
   )

   if response.approved:
       delete_files(file_list)
   else:
       print(f"Deletion denied: {response.reason}")
   ```

2. **Handle approval responses.**
   Respond to pending approval requests:
   ```python
   pending = approval.get_pending_approvals("delete_files")

   for request in pending:
       # Review request details
       print(f"Request: {request.context}")

       # Respond based on your criteria
       approval.respond_to_approval(
           request.request_id,
           approved=True,
           responder="admin_user",
           reason="Files confirmed safe to delete"
       )
   ```

## Use CLI analysis commands

1. **Run telemetry analysis.**
   The telemetry CLI provides several analysis commands:
   ```bash
   # Show recent telemetry data
   python -m attune.telemetry show

   # Display cost savings analysis
   python -m attune.telemetry savings

   # Check Sonnet to Opus fallback metrics
   python -m attune.telemetry sonnet-opus-analysis

   # View agent performance metrics
   python -m attune.telemetry agent-performance
   ```

2. **Check test and automation status.**
   Monitor system health through status commands:
   ```bash
   # Per-file test status
   python -m attune.telemetry file-test-status

   # Comprehensive Tier 1 automation status
   python -m attune.telemetry tier1-status

   # Task routing analysis
   python -m attune.telemetry task-routing-report
   ```

## Verification

Your telemetry integration works correctly when:
- Coordination signals are received by target agents within their TTL period
- Agent heartbeats appear in the active agents list with current status
- Approval requests pause workflow execution until human response
- Event streams contain your published events with correct timestamps
- CLI commands display current telemetry data without errors
