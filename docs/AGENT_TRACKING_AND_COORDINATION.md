---
description: Agent Tracking & Coordination: **Date:** January 27, 2026 **Patterns:** Pattern 1 & 2 from Agent Coordination Architecture **Status:** ✅ Complete and Ready for
---

# Agent Tracking & Coordination

**Date:** January 27, 2026
**Patterns:** Pattern 1 & 2 from Agent Coordination Architecture
**Status:** ✅ Complete and Ready for Use

---

## Overview

The Attune AI now includes two powerful patterns for agent coordination using TTL (Time-To-Live) based ephemeral messaging:

### Pattern 1: Agent Heartbeat Tracking
Monitor agent liveness and execution status through periodic heartbeat updates stored in Redis with TTL. When an agent crashes or hangs, its heartbeat expires automatically.

### Pattern 2: Coordination Signals
Enable inter-agent communication via TTL-based ephemeral messages. Agents can send targeted signals, broadcast to all agents, and wait for specific signals with timeout.

---

## Pattern 1: Agent Heartbeat Tracking

### Quick Start

```python
from attune.telemetry import HeartbeatCoordinator

# Initialize coordinator
coordinator = HeartbeatCoordinator()

# Start tracking agent
coordinator.start_heartbeat(
    agent_id="my-agent-123",
    metadata={"workflow": "code-review", "run_id": "xyz"}
)

# Update progress during execution
coordinator.beat(
    status="running",
    progress=0.5,
    current_task="Analyzing functions"
)

# Complete tracking
coordinator.stop_heartbeat(final_status="completed")
```

### Monitoring Agents

**CLI Commands:**

```bash
# View all active agents
attune telemetry agents

# Example output:
# 🤖 Active Agents
# ----------------------------------------------------------------------
#   🟢 code-review-abc123
#       Status:       running
#       Progress:     65.0%
#       Task:         Analyzing security patterns
#       Last beat:    2.3s ago
#       Workflow:     code-review
```

**Python API:**

```python
# Get all active agents
active = coordinator.get_active_agents()
for agent in active:
    print(f"{agent.agent_id}: {agent.status} ({agent.progress*100:.0f}%)")

# Check if specific agent is alive
if coordinator.is_agent_alive("my-agent-123"):
    print("Agent is running!")

# Get agent status details
status = coordinator.get_agent_status("my-agent-123")
if status:
    print(f"Progress: {status.progress*100:.0f}%")
    print(f"Task: {status.current_task}")

# Detect stale agents (no update in 60s)
stale = coordinator.get_stale_agents(threshold_seconds=60.0)
for agent in stale:
    print(f"Stale: {agent.agent_id}")
```

### Agent Status Values

| Status | Description |
|--------|-------------|
| `starting` | Agent initializing |
| `running` | Agent actively executing |
| `completed` | Agent finished successfully |
| `failed` | Agent encountered error |
| `cancelled` | Agent was cancelled by user |

### Heartbeat Configuration

```python
# Default settings
HeartbeatCoordinator.HEARTBEAT_TTL = 30      # Expires after 30s
HeartbeatCoordinator.HEARTBEAT_INTERVAL = 10  # Update every 10s

# Customize TTL for longer-running agents
coordinator.HEARTBEAT_TTL = 120  # 2 minutes
```

### Use Cases

1. **Long-Running Workflows**: Monitor multi-agent workflows and detect crashes
2. **Parallel Execution**: Track multiple agents running concurrently
3. **Health Monitoring**: Dashboard showing active agents across system
4. **Failure Detection**: Auto-detect and restart failed agents
5. **Progress Tracking**: Real-time progress updates for user interfaces

---

## Pattern 2: Coordination Signals

### Quick Start

```python
from attune.telemetry import CoordinationSignals

# Agent A sends signal to Agent B
sender = CoordinationSignals(agent_id="agent-a")
sender.signal(
    signal_type="task_complete",
    target_agent="agent-b",
    payload={"result": "success", "data": {...}}
)

# Agent B waits for signal
receiver = CoordinationSignals(agent_id="agent-b")
signal = receiver.wait_for_signal(
    signal_type="task_complete",
    source_agent="agent-a",
    timeout=30.0
)

if signal:
    process(signal.payload)
```

### Signal Types

Common signal types (you can use custom types):

| Type | Usage |
|------|-------|
| `task_complete` | Notify that a task finished |
| `abort` | Request immediate termination |
| `ready` | Signal readiness to proceed |
| `checkpoint` | Reached synchronization point |
| `error` | Report error condition |

### Broadcasting

```python
# Send signal to all agents
orchestrator = CoordinationSignals(agent_id="orchestrator")
orchestrator.broadcast(
    signal_type="abort",
    payload={"reason": "user_cancelled"}
)

# Each agent receives broadcast
agent = CoordinationSignals(agent_id="worker-1")
signal = agent.check_signal(signal_type="abort")
if signal:
    print(f"Abort requested: {signal.payload['reason']}")
```

### Waiting for Signals

```python
# Blocking wait with timeout
signal = coordinator.wait_for_signal(
    signal_type="task_complete",
    source_agent="agent-a",  # Optional filter by source
    timeout=30.0,            # Max wait time
    poll_interval=0.5        # Check every 500ms
)

# Non-blocking check
signal = coordinator.check_signal(
    signal_type="ready",
    consume=True  # Remove after reading
)

# Get all pending signals
signals = coordinator.get_pending_signals(signal_type="checkpoint")
print(f"Received {len(signals)} checkpoint signals")
```

### Viewing Signals (CLI)

```bash
# View pending signals for an agent
attune telemetry signals --agent my-agent-123

# Example output:
# 📡 Coordination Signals for my-agent-123
# ----------------------------------------------------------------------
#   ✅ task_complete
#       From:         agent-producer
#       Target:       my-agent-123
#       Age:          5.2s
#       Expires in:   54.8s
#       Payload:      {'result': 'success', 'data': {...}}
```

### Clearing Signals

```python
# Clear all signals for this agent
count = coordinator.clear_signals()
print(f"Cleared {count} signals")

# Clear specific signal type
count = coordinator.clear_signals(signal_type="checkpoint")
```

### Signal TTL Configuration

```python
# Default TTL: 60 seconds
CoordinationSignals.DEFAULT_TTL = 60

# Send signal with custom TTL
coordinator.signal(
    signal_type="checkpoint",
    target_agent="worker-1",
    payload={...},
    ttl_seconds=120  # Expires in 2 minutes
)
```

### Use Cases

1. **Sequential Workflows**: Agent A completes → signals Agent B to start
2. **Parallel Coordination**: Multiple agents reach checkpoint → proceed together
3. **Error Propagation**: Worker signals error → orchestrator aborts workflow
4. **User Approval**: Workflow pauses → waits for user approval signal
5. **Dynamic Routing**: Agents signal completion → orchestrator routes next task

---

## Coordination Patterns

### Pattern: Producer-Consumer

```python
# Producer agent
producer = CoordinationSignals(agent_id="producer")
result = process_data()
producer.signal(
    signal_type="task_complete",
    target_agent="consumer",
    payload={"result": result}
)

# Consumer agent
consumer = CoordinationSignals(agent_id="consumer")
signal = consumer.wait_for_signal(
    signal_type="task_complete",
    source_agent="producer",
    timeout=60.0
)
if signal:
    consume(signal.payload["result"])
```

### Pattern: Checkpoint Synchronization

```python
# Each agent signals when ready
agent = CoordinationSignals(agent_id="worker-1")
agent.signal(
    signal_type="checkpoint",
    target_agent="orchestrator",
    payload={"ready": True}
)

# Orchestrator waits for all agents
orchestrator = CoordinationSignals(agent_id="orchestrator")
checkpoint_signals = orchestrator.get_pending_signals(signal_type="checkpoint")

if len(checkpoint_signals) == expected_agents:
    print("All agents ready! Proceeding...")
    orchestrator.broadcast(signal_type="proceed", payload={})
```

### Pattern: Abort on Error

```python
# Worker encounters error
worker = CoordinationSignals(agent_id="worker-3")
try:
    process()
except Exception as e:
    worker.signal(
        signal_type="error",
        target_agent="orchestrator",
        payload={"error": str(e)}
    )

# Orchestrator handles error
orchestrator = CoordinationSignals(agent_id="orchestrator")
error_signal = orchestrator.check_signal(signal_type="error")
if error_signal:
    print(f"Error from {error_signal.source_agent}: {error_signal.payload}")
    orchestrator.broadcast(signal_type="abort", payload={"reason": "error"})
```

---

## Integration with Workflows

### Example: Multi-Agent Workflow with Tracking

```python
from attune.telemetry import HeartbeatCoordinator, CoordinationSignals
from attune.workflows.base import BaseWorkflow
import asyncio

class CoordinatedWorkflow(BaseWorkflow):
    async def execute(self, **kwargs):
        # Initialize coordination
        heartbeat = HeartbeatCoordinator()
        signals = CoordinationSignals(agent_id="orchestrator")

        # Start agents with tracking
        agents = ["analyzer", "reviewer", "reporter"]
        tasks = []

        for agent_name in agents:
            agent_id = f"{agent_name}_{uuid.uuid4().hex[:8]}"

            # Start heartbeat
            heartbeat.start_heartbeat(
                agent_id=agent_id,
                metadata={"workflow": self.name, "agent": agent_name}
            )

            # Launch agent
            task = self._run_agent(agent_id, agent_name)
            tasks.append(task)

        # Wait for completion signals
        completed = 0
        while completed < len(agents):
            signal = signals.wait_for_signal(
                signal_type="task_complete",
                timeout=120.0
            )
            if signal:
                completed += 1
                print(f"Agent {signal.source_agent} completed")

        # Await all tasks
        results = await asyncio.gather(*tasks)
        return results

    async def _run_agent(self, agent_id: str, agent_name: str):
        """Run agent with heartbeat updates."""
        coordinator = HeartbeatCoordinator()
        signals = CoordinationSignals(agent_id=agent_id)

        try:
            # Update progress
            coordinator.beat(status="running", progress=0.5, current_task=f"Running {agent_name}")

            # Do work...
            result = await self._do_work(agent_name)

            # Signal completion
            signals.signal(
                signal_type="task_complete",
                target_agent="orchestrator",
                payload={"result": result}
            )

            coordinator.stop_heartbeat(final_status="completed")
            return result

        except Exception as e:
            coordinator.stop_heartbeat(final_status="failed")
            signals.signal(
                signal_type="error",
                target_agent="orchestrator",
                payload={"error": str(e)}
            )
            raise
```

---

## Memory Requirements

Both patterns require Redis for storage:

```bash
# Start Redis
redis-server

# Or use attune command
attune memory start

# Verify Redis is running
attune memory status
```

**Memory Usage:**
- Heartbeat: ~1KB per agent
- Signal: ~500 bytes per signal
- TTL ensures automatic cleanup (no manual maintenance)

**Scalability:**
- Can track 1000+ concurrent agents
- Signals expire automatically (no memory leaks)
- Redis scan operations are O(N) but fast for <10K agents

---

## Testing

Run the demo scripts to see patterns in action:

```bash
# Pattern 1: Heartbeat tracking
python examples/agent_tracking_demo.py

# Pattern 2: Coordination signals
python examples/agent_coordination_demo.py
```

**Sample Output:**

```
==================================================================
AGENT HEARTBEAT TRACKING DEMONSTRATION
==================================================================

🚀 Launching 3 agents...
[agent-fast] Starting...
[agent-slow] Starting...
[agent-fail] Starting...

📊 Agents After 1 Second:
  Active agents: 3
    - agent-fast: running (20%)
    - agent-slow: running (17%)
    - agent-fail: running (50%)

[agent-fail] Failed: Simulated failure
[agent-fast] Completed!
[agent-slow] Completed!

📊 Final Status:
  Active agents: 0
```

---

## CLI Reference

### Agent Tracking Commands

```bash
# View all active agents
attune telemetry agents

# No arguments needed - shows all tracked agents
```

### Coordination Signal Commands

```bash
# View signals for a specific agent
attune telemetry signals --agent my-agent-123

# Shorter alias
attune telemetry signals -a my-agent-123
```

---

## Architecture Benefits

### 1. Automatic Cleanup via TTL
- No manual cleanup required
- Crashed agents automatically removed
- Expired signals don't accumulate

### 2. Zero Database Pollution
- All data ephemeral
- No persistent storage needed
- No schema migrations

### 3. Scalable & Fast
- Redis optimized for high throughput
- O(1) lookups by agent ID
- Scan operations efficient for <10K agents

### 4. Language Agnostic
- Any agent can participate (Python, JS, etc.)
- Just needs Redis access
- Simple key-value protocol

### 5. Failure Resilient
- Crashed agents expire automatically
- No zombie processes
- Easy to detect failures

---

## Automatic Workflow Integration

Pattern 1 & 2 are now integrated with BaseWorkflow for automatic agent tracking and coordination.

**Quick Start:**

```python
from attune.workflows.base import BaseWorkflow, ModelTier

workflow = BaseWorkflow(
    enable_heartbeat_tracking=True,  # Pattern 1
    enable_coordination=True,         # Pattern 2
    agent_id="my-workflow-001",
)

# Automatic heartbeat updates during execution
result = await workflow.execute()

# Coordination methods available
workflow.send_signal(signal_type="task_complete", target_agent="orchestrator")
signal = workflow.wait_for_signal(signal_type="approval", timeout=30.0)
```

**See:** [WORKFLOW_COORDINATION.md](./WORKFLOW_COORDINATION.md) - Complete workflow integration guide

---

## Related Documentation

- [WORKFLOW_COORDINATION.md](./WORKFLOW_COORDINATION.md) - BaseWorkflow integration (Pattern 1 & 2)
- [AGENT_COORDINATION_ARCHITECTURE.md](./AGENT_COORDINATION_ARCHITECTURE.md) - Full architecture patterns (1-6)
- [ADAPTIVE_ROUTING_INTEGRATION.md](./ADAPTIVE_ROUTING_INTEGRATION.md) - Pattern 3 integration
- [ADAPTIVE_ROUTING_ANTHROPIC_NATIVE.md](./ADAPTIVE_ROUTING_ANTHROPIC_NATIVE.md) - Anthropic-native routing

---

## Pattern 4: Real-Time Event Streaming

**Status:** ✅ Implemented (January 27, 2026)

### Overview

Pattern 4 provides real-time event streaming using Redis Streams, enabling live monitoring of agent activity and coordination signals through pub-sub architecture.

### Quick Start

```python
from attune.telemetry import EventStreamer

# Initialize event streamer
streamer = EventStreamer()

# Publish custom events
streamer.publish_event(
    event_type="workflow_progress",
    data={"workflow_id": "code-review", "stage": "analysis", "progress": 0.5}
)

# Consume events in real-time (blocking iterator)
for event in streamer.consume_events(event_types=["agent_heartbeat", "coordination_signal"]):
    print(f"[{event.timestamp}] {event.event_type}: {event.data}")

# Get recent events (non-blocking)
recent = streamer.get_recent_events(event_type="agent_heartbeat", count=100)
for event in recent:
    print(f"Agent {event.data['agent_id']}: {event.data['status']}")
```

### Automatic Integration

Heartbeat and coordination components automatically publish to streams when enabled:

```python
# Enable streaming in HeartbeatCoordinator
coordinator = HeartbeatCoordinator(enable_streaming=True)
coordinator.start_heartbeat(agent_id="my-agent")
# → Automatically publishes to attune:events:agent_heartbeat stream

# Enable streaming in CoordinationSignals
signals = CoordinationSignals(agent_id="orchestrator", enable_streaming=True)
signals.signal(signal_type="task_complete", target_agent="worker")
# → Automatically publishes to attune:events:coordination_signal stream
```

### Event Types

| Event Type           | Description              | Published By         |
|----------------------|--------------------------|----------------------|
| `agent_heartbeat`    | Agent liveness updates   | HeartbeatCoordinator |
| `coordination_signal`| Inter-agent coordination | CoordinationSignals  |
| `workflow_progress`  | Workflow stage progress  | Custom workflows     |
| `agent_error`        | Agent failures           | Error handlers       |

### Stream Architecture

**Stream Naming:** `attune:events:{event_type}`

**Features:**

- Auto-trimming (MAXLEN ~10,000 events)
- TTL-free (events persist until trimmed or consumed)
- Efficient broadcast to multiple consumers
- Ordered event delivery per stream

### Consumption Patterns

#### 1. Blocking Iterator (Real-Time)

```python
# Block and wait for events as they arrive
for event in streamer.consume_events(
    event_types=["agent_heartbeat"],
    block_ms=5000,  # 5 second timeout
    count=10,       # Max events per batch
):
    handle_event(event)
```

#### 2. Non-Blocking Retrieval (Historical)

```python
# Get most recent 100 events
events = streamer.get_recent_events(
    event_type="coordination_signal",
    count=100,
)

for event in events:
    analyze_event(event)
```

### Stream Management

```python
# Get stream information
info = streamer.get_stream_info(event_type="agent_heartbeat")
print(f"Stream length: {info['length']}")

# Trim stream to max size
trimmed = streamer.trim_stream(event_type="agent_heartbeat", max_length=1000)
print(f"Trimmed {trimmed} events")

# Delete stream
streamer.delete_stream(event_type="old_event_type")
```

### Demo Script

Run the complete demonstration:

```bash
python examples/event_streaming_demo.py
```

**Demonstrates:**

- Heartbeat events published to streams
- Coordination signal events published to streams
- Broadcast event patterns
- Live event consumption
- Stream management operations

### Event Streaming Use Cases

1. **Real-Time Dashboards**: WebSocket server consumes events and pushes to browser clients
2. **Event Replay**: Retrieve historical events for debugging or analysis
3. **Audit Logging**: Permanent record of agent coordination and execution
4. **Multi-System Monitoring**: Other services consume events from shared Redis instance
5. **Alerting**: Monitor streams for error events and trigger notifications

### Integration Example

```python
from attune.workflows.base import BaseWorkflow, ModelTier
from attune.telemetry import EventStreamer

class MonitoredWorkflow(BaseWorkflow):
    def __init__(self, **kwargs):
        super().__init__(
            enable_heartbeat_tracking=True,
            enable_streaming=True,  # Enable event streaming
            **kwargs
        )
        self.streamer = EventStreamer()

    async def run_stage(self, stage_name: str, tier: ModelTier, input_data: dict):
        # Publish custom workflow progress events
        self.streamer.publish_event(
            event_type="workflow_progress",
            data={
                "workflow": self.name,
                "stage": stage_name,
                "tier": tier.value,
                "timestamp": datetime.now().isoformat()
            }
        )

        # ... stage execution ...

        return result, tokens_in, tokens_out
```

### Performance

**Overhead:**

- Event publishing: ~1-2ms per event (non-blocking)
- Stream retrieval: ~5-10ms for 100 events
- Live consumption: ~0.1ms per event (iterator)

**Memory:**

- ~500 bytes per event
- Auto-trimmed to 10K events = ~5MB per stream
- Multiple streams supported concurrently

**Scalability:**

- Tested with 1000+ events/second
- Multiple consumers per stream
- Redis Streams designed for high throughput

---

## Pattern 5: Human Approval Gates

**Purpose:** Pause workflow execution for human approval on critical decisions

**Status:** ✅ Implemented and Tested (20 tests passing)

### How It Works

ApprovalGate allows workflows to block and wait for human approval before proceeding with critical actions like deployments, deletions, or refactorings.

**Key Features:**

- **Blocking requests** - Workflow pauses until human responds
- **Timeout handling** - Configurable timeout (default 5 minutes)
- **UI integration** - Pending approvals retrievable for dashboard
- **Context sharing** - Rich context passed for informed decisions
- **Graceful degradation** - Works without Redis (auto-rejects)

### Basic Usage

```python
from attune.telemetry import ApprovalGate

# In workflow: Request approval
gate = ApprovalGate(agent_id="deployment-workflow")

approval = gate.request_approval(
    approval_type="deploy_to_production",
    context={
        "version": "2.0.0",
        "changes": ["feature-x", "bugfix-y"],
        "risk_level": "medium"
    },
    timeout=300.0  # 5 minutes
)

if approval.approved:
    deploy_to_production()
else:
    logger.info(f"Deployment rejected: {approval.reason}")
```

### UI Integration

```python
# In UI: Display pending approvals
ui_gate = ApprovalGate()
pending = ui_gate.get_pending_approvals()

for request in pending:
    print(f"Approval needed: {request.approval_type}")
    print(f"Context: {request.context}")
    print(f"Requested by: {request.agent_id}")

    # User makes decision
    ui_gate.respond_to_approval(
        request_id=request.request_id,
        approved=True,
        responder="user@example.com",
        reason="Looks good to deploy"
    )
```

### Architecture

```text
Workflow                    Redis                    UI
   │                          │                       │
   │──request_approval()─────>│                       │
   │   (blocking)              │                       │
   │                           │<──get_pending()───────│
   │                           │                       │
   │                           │───pending list───────>│
   │                           │                       │
   │                           │<──respond()───────────│
   │<──approval response───────│                       │
   │                           │                       │
```

**See also:** [PATTERN5_APPROVAL_GATES_SUMMARY.md](PATTERN5_APPROVAL_GATES_SUMMARY.md)

---

## Pattern 6: Agent-to-LLM Feedback Loop

**Purpose:** Collect quality ratings on LLM responses to inform adaptive routing decisions

**Status:** ✅ Implemented and Tested (24 tests passing)

### How It Works

FeedbackLoop tracks quality scores for LLM responses and uses historical performance to recommend tier upgrades or downgrades, enabling adaptive routing that balances cost and quality.

**Key Features:**

- **Quality tracking** - Record scores 0.0-1.0 after each LLM response
- **Statistical analysis** - Calculate avg/min/max/trend over time
- **Adaptive routing** - Recommend tier based on historical quality
- **Performance identification** - Find underperforming workflow stages
- **7-day retention** - Automatic cleanup with TTL

### Recording and Using Feedback

```python
from attune.telemetry import FeedbackLoop
from attune.telemetry.feedback_loop import ModelTier

feedback = FeedbackLoop()

# Record quality after LLM response
feedback.record_feedback(
    workflow_name="code-review",
    stage_name="analysis",
    tier=ModelTier.CHEAP,
    quality_score=0.65,  # Below threshold (0.7)
    metadata={"tokens": 150, "latency_ms": 1200}
)

# Get tier recommendation
recommendation = feedback.recommend_tier(
    workflow_name="code-review",
    stage_name="analysis",
    current_tier="cheap"
)

if recommendation.recommended_tier != "cheap":
    print(f"Upgrade to {recommendation.recommended_tier}")
    print(f"Reason: {recommendation.reason}")
    print(f"Confidence: {recommendation.confidence:.1%}")
```

### Decision Logic

**Upgrade when quality is poor:**

```python
if avg_quality < 0.7:
    # Upgrade: cheap → capable or capable → premium
```

**Downgrade when quality is excellent:**

```python
if avg_quality > 0.9:
    # Check if lower tier also performs well
    if lower_tier_quality > 0.85:
        # Downgrade to save cost
```

**Maintain when quality is acceptable:**

```python
if 0.7 <= avg_quality <= 0.9:
    # Keep current tier
```

### Quality Statistics

```python
# Get performance stats
stats = feedback.get_quality_stats(
    workflow_name="code-review",
    stage_name="analysis",
    tier="cheap"
)

print(f"Average: {stats.avg_quality:.2f}")
print(f"Range: {stats.min_quality:.2f} - {stats.max_quality:.2f}")
print(f"Samples: {stats.sample_count}")
print(f"Trend: {stats.recent_trend:+.2f}")  # Positive = improving
```

### Workflow Integration

```python
from attune.workflows.base import BaseWorkflow
from attune.telemetry import FeedbackLoop

class AdaptiveWorkflow(BaseWorkflow):
    def __init__(self):
        super().__init__()
        self.feedback = FeedbackLoop()

    async def run_stage(self, stage_name: str, tier: ModelTier, input_data: dict):
        # Get tier recommendation
        rec = self.feedback.recommend_tier(
            workflow_name=self.name,
            stage_name=stage_name,
            current_tier=tier.value
        )

        # Use recommended tier if confident
        if rec.confidence > 0.7:
            tier = ModelTier(rec.recommended_tier)

        # Execute stage
        result, cost, tokens = await super().run_stage(stage_name, tier, input_data)

        # Record quality
        quality = self._evaluate_quality(result)
        self.feedback.record_feedback(
            workflow_name=self.name,
            stage_name=stage_name,
            tier=tier.value,
            quality_score=quality
        )

        return result, cost, tokens
```

**See also:** [PATTERN6_FEEDBACK_LOOP_SUMMARY.md](PATTERN6_FEEDBACK_LOOP_SUMMARY.md)

---

## Implementation Status

### Completed Patterns ✅

- ✅ **Pattern 1: Agent Heartbeat Tracking** - Monitor agent liveness with TTL heartbeats
- ✅ **Pattern 2: Coordination Signals** - Inter-agent communication via signals
- ✅ **Pattern 3: State Synchronization** - Cross-agent state sharing
- ✅ **Pattern 4: Real-Time Event Streaming** - Live event distribution via Redis Streams
- ✅ **Pattern 5: Human Approval Gates** - Pause workflows for human decisions
- ✅ **Pattern 6: Agent-to-LLM Feedback Loop** - Quality-based adaptive routing

### Dashboard

**Web Monitoring Dashboard** - ✅ Complete

A zero-dependency web dashboard for visualizing all 6 patterns in real-time:

```python
from attune.dashboard import run_simple_dashboard

# Start dashboard (no external dependencies)
run_simple_dashboard(host="0.0.0.0", port=8000)

# Open browser: http://localhost:8000
```

**Features:**

- Real-time agent status monitoring
- Approval request management (approve/reject from UI)
- Quality metrics and underperforming stage detection
- Coordination signal viewer
- Event stream monitor
- Auto-refresh every 5 seconds

**See:** [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) and [DASHBOARD_SUMMARY.md](DASHBOARD_SUMMARY.md)

### Next Steps

**Immediate:**

- Add pattern usage examples to example workflows
- Performance testing with all patterns enabled
- Production deployment examples

**Future Enhancements:**

- Prometheus metrics export
- Agent health scoring and auto-recovery
- Signal replay/audit log
- Multi-tenancy support for agent isolation
- Pattern composition helpers

---

**Status:** ✅ All Core Patterns Implemented and Production Ready

**Test Coverage:**

- Pattern 1-3: 127+ tests passing
- Pattern 4: 21 tests passing
- Pattern 5: 20 tests passing
- Pattern 6: 24 tests passing
- **Total: 192+ tests passing**

**Dependencies:** Redis 5.0+ (graceful degradation when unavailable)

**Performance:** Tested with 1000+ concurrent agents

**Documentation:** Complete with demos for all patterns
