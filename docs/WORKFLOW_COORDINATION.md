---
description: Workflow Coordination & Agent Tracking: **Date:** January 27, 2026 **Version:** 4.8.2 **Status:** ✅ Complete and Ready for Use --- ## Overview The Empathy Frame
---

# Workflow Coordination & Agent Tracking

**Date:** February 10, 2026
**Version:** 5.0.0
**Status:** ✅ Complete and Ready for Use

---

## Overview

Attune AI supports agent tracking and coordination in BaseWorkflow, enabling workflows to:

- **Track agent liveness** via TTL-based heartbeat updates (Pattern 1)
- **Coordinate between agents** via TTL-based ephemeral signals (Pattern 2)
- **Persist state across sessions** via AgentStateStore with checkpoints and recovery (Pattern 3 - NEW in v2.5.0)
- **Delegate stages to multi-agent teams** via MultiAgentStageMixin (Pattern 4 - NEW in v2.5.0)
- **Compose workflows into teams** via WorkflowComposer and WorkflowAgentAdapter (Pattern 5 - NEW in v2.5.0)

These features integrate seamlessly with the existing workflow infrastructure, requiring only optional flags to enable.

---

## Quick Start

### Enable Heartbeat Tracking

```python
from attune.workflows.base import BaseWorkflow, ModelTier

class MyWorkflow(BaseWorkflow):
    name = "my-workflow"
    stages = ["stage1", "stage2"]
    tier_map = {
        "stage1": ModelTier.CHEAP,
        "stage2": ModelTier.CAPABLE,
    }

# Enable heartbeat tracking
workflow = MyWorkflow(
    enable_heartbeat_tracking=True,
    agent_id="my-workflow-001",  # Optional: auto-generated if None
)

# Execute workflow - heartbeats published automatically
result = await workflow.execute(input_data)
```

**What happens automatically:**
1. Heartbeat started at workflow launch
2. Progress updates published before/after each stage
3. Final heartbeat on completion/failure
4. Automatic cleanup via TTL (30s default)

### Enable Coordination Signals

```python
# Enable coordination between workflows
producer = MyWorkflow(
    enable_coordination=True,
    agent_id="producer",
)

consumer = MyWorkflow(
    enable_coordination=True,
    agent_id="consumer",
)

# Producer signals completion to consumer
await producer.execute()

# Consumer waits for producer signal
signal = consumer.wait_for_signal(
    signal_type="task_complete",
    source_agent="producer",
    timeout=30.0
)
```

---

## Workflow API

### Initialization Parameters

```python
BaseWorkflow(
    # ... existing parameters ...
    enable_heartbeat_tracking: bool = False,
    enable_coordination: bool = False,
    agent_id: str | None = None,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_heartbeat_tracking` | `bool` | `False` | Enable TTL-based heartbeat tracking |
| `enable_coordination` | `bool` | `False` | Enable coordination signals |
| `agent_id` | `str \| None` | Auto-generated | Agent identifier (format: `{workflow_name}-{run_id}`) |

**Requirements:**
- Redis backend must be running
- If Redis is unavailable, features gracefully degrade (warnings logged)

---

## Coordination Methods

### send_signal()

Send a coordination signal to another agent.

```python
workflow.send_signal(
    signal_type: str,
    target_agent: str | None = None,
    payload: dict[str, Any] | None = None,
    ttl_seconds: int | None = None,
) -> str
```

**Parameters:**
- `signal_type`: Type of signal (e.g., "task_complete", "checkpoint", "error")
- `target_agent`: Target agent ID (None for broadcast to all agents)
- `payload`: Optional signal payload data
- `ttl_seconds`: Optional TTL override (default 60 seconds)

**Returns:**
- Signal ID if coordination is enabled, empty string otherwise

**Example:**
```python
# Targeted signal
workflow.send_signal(
    signal_type="task_complete",
    target_agent="orchestrator",
    payload={"result": "success", "data": {...}}
)

# Broadcast to all agents
workflow.send_signal(
    signal_type="abort",
    target_agent=None,  # Broadcast
    payload={"reason": "user_cancelled"}
)
```

---

### wait_for_signal()

Wait for a coordination signal from another agent (blocking).

```python
workflow.wait_for_signal(
    signal_type: str,
    source_agent: str | None = None,
    timeout: float = 30.0,
    poll_interval: float = 0.5,
) -> CoordinationSignal | None
```

**Parameters:**
- `signal_type`: Type of signal to wait for
- `source_agent`: Optional source agent filter
- `timeout`: Maximum wait time in seconds
- `poll_interval`: Poll interval in seconds

**Returns:**
- `CoordinationSignal` if received, `None` if timeout

**Example:**
```python
# Wait for orchestrator approval
signal = workflow.wait_for_signal(
    signal_type="approval",
    source_agent="orchestrator",
    timeout=60.0
)

if signal:
    proceed_with_deployment(signal.payload)
else:
    raise TimeoutError("No approval received")
```

---

### check_signal()

Check for a coordination signal without blocking (non-blocking).

```python
workflow.check_signal(
    signal_type: str,
    source_agent: str | None = None,
    consume: bool = True,
) -> CoordinationSignal | None
```

**Parameters:**
- `signal_type`: Type of signal to check for
- `source_agent`: Optional source agent filter
- `consume`: If True, remove signal after reading

**Returns:**
- `CoordinationSignal` if available, `None` otherwise

**Example:**
```python
# Non-blocking check for abort signal
signal = workflow.check_signal(signal_type="abort")
if signal:
    raise WorkflowAbortedException(signal.payload["reason"])
```

---

## Coordination Patterns

### Pattern: Producer-Consumer

Producer workflow generates data and signals consumer:

```python
class ProducerWorkflow(BaseWorkflow):
    name = "producer"
    stages = ["generate", "validate", "notify"]

    async def run_stage(self, stage_name: str, tier: ModelTier, input_data: dict):
        if stage_name == "notify":
            # Signal completion to consumer
            self.send_signal(
                signal_type="task_complete",
                target_agent="consumer",
                payload={"data": result_data}
            )
        # ... rest of stage logic

class ConsumerWorkflow(BaseWorkflow):
    name = "consumer"
    stages = ["wait", "process", "report"]

    async def run_stage(self, stage_name: str, tier: ModelTier, input_data: dict):
        if stage_name == "wait":
            # Wait for producer signal
            signal = self.wait_for_signal(
                signal_type="task_complete",
                source_agent="producer",
                timeout=30.0
            )
            if signal is None:
                raise TimeoutError("Producer timeout")

            return signal.payload, 0, 0
        # ... rest of stage logic

# Run concurrently
producer = ProducerWorkflow(enable_coordination=True, agent_id="producer")
consumer = ConsumerWorkflow(enable_coordination=True, agent_id="consumer")

producer_task = asyncio.create_task(producer.execute())
consumer_task = asyncio.create_task(consumer.execute())

await asyncio.gather(producer_task, consumer_task)
```

---

### Pattern: Checkpoint Synchronization

Multiple agents synchronize at checkpoints:

```python
class WorkerWorkflow(BaseWorkflow):
    async def run_stage(self, stage_name: str, tier: ModelTier, input_data: dict):
        if stage_name == "checkpoint":
            # Signal checkpoint reached
            self.send_signal(
                signal_type="checkpoint",
                target_agent="orchestrator",
                payload={"status": "ready"}
            )

            # Wait for proceed signal
            signal = self.wait_for_signal(
                signal_type="proceed",
                source_agent="orchestrator",
                timeout=60.0
            )
            # ... continue

class OrchestratorWorkflow(BaseWorkflow):
    async def run_stage(self, stage_name: str, tier: ModelTier, input_data: dict):
        if stage_name == "wait_checkpoint":
            # Wait for all workers
            expected_workers = 3
            checkpoints = []

            for _ in range(expected_workers):
                signal = self.wait_for_signal(
                    signal_type="checkpoint",
                    timeout=120.0
                )
                checkpoints.append(signal)

            # Broadcast proceed to all workers
            self.send_signal(
                signal_type="proceed",
                target_agent=None,  # Broadcast
                payload={"timestamp": datetime.now().isoformat()}
            )
```

---

### Pattern: Abort on Error

One workflow signals abort, all others check periodically:

```python
class WorkerWorkflow(BaseWorkflow):
    async def run_stage(self, stage_name: str, tier: ModelTier, input_data: dict):
        # Check for abort before each stage
        abort_signal = self.check_signal(signal_type="abort")
        if abort_signal:
            reason = abort_signal.payload.get("reason", "unknown")
            raise WorkflowAbortedException(f"Aborted: {reason}")

        # On error, signal abort to others
        try:
            result = process_work()
        except Exception as e:
            self.send_signal(
                signal_type="abort",
                target_agent=None,  # Broadcast
                payload={"reason": str(e), "source": self._agent_id}
            )
            raise

# Run multiple workers
workers = [
    WorkerWorkflow(enable_coordination=True, agent_id=f"worker-{i}")
    for i in range(5)
]

tasks = [asyncio.create_task(w.execute()) for w in workers]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

---

## Heartbeat Tracking Integration

### Automatic Heartbeat Updates

When `enable_heartbeat_tracking=True`, BaseWorkflow automatically:

1. **Start Heartbeat** - On `execute()` call
```python
{
    "agent_id": "my-workflow-abc12345",
    "status": "starting",
    "progress": 0.0,
    "current_task": "initializing",
    "metadata": {
        "workflow": "my-workflow",
        "run_id": "abc12345",
        "provider": "anthropic",
        "stages": 3
    }
}
```

2. **Stage Start Update** - Before each stage
```python
{
    "status": "running",
    "progress": 0.33,  # stage_index / len(stages)
    "current_task": "Running stage: stage1 (cheap)"
}
```

3. **Stage Completion Update** - After each stage
```python
{
    "status": "running",
    "progress": 0.66,
    "current_task": "Completed stage: stage1"
}
```

4. **Final Status** - On workflow completion
```python
{
    "status": "completed",  # or "failed"
    "progress": 1.0
}
```

### Monitoring Active Workflows

```bash
# CLI: View all active agents
attune telemetry agents

# Output:
# 🤖 Active Agents
# ----------------------------------------------------------------------
#   🟢 producer-abc12345
#       Status:       running
#       Progress:     66.7%
#       Task:         Running stage: validate (capable)
#       Last beat:    2.3s ago
#       Workflow:     producer
```

**Python API:**
```python
from attune.telemetry import HeartbeatCoordinator

coordinator = HeartbeatCoordinator()

# Get all active agents
active = coordinator.get_active_agents()
for agent in active:
    print(f"{agent.agent_id}: {agent.status} ({agent.progress*100:.0f}%)")

# Check if specific workflow is alive
if coordinator.is_agent_alive("my-workflow-abc12345"):
    print("Workflow is running!")

# Detect stale workflows (no update in 60s)
stale = coordinator.get_stale_agents(threshold_seconds=60.0)
```

---

## Configuration

### Redis Requirements

Both heartbeat tracking and coordination require Redis:

```bash
# Start Redis
redis-server

# Or use Empathy command
attune memory start

# Verify Redis is running
attune memory status
```

### TTL Configuration

**Heartbeat TTL** (default: 30 seconds):
```python
from attune.telemetry import HeartbeatCoordinator

HeartbeatCoordinator.HEARTBEAT_TTL = 60  # Increase for longer-running workflows
```

**Signal TTL** (default: 60 seconds):
```python
from attune.telemetry import CoordinationSignals

CoordinationSignals.DEFAULT_TTL = 120  # Increase for slower coordination

# Or per-signal:
workflow.send_signal(
    signal_type="checkpoint",
    target_agent="orchestrator",
    payload={...},
    ttl_seconds=300  # 5 minutes
)
```

### Graceful Degradation

When Redis is unavailable:
- Warnings logged: `"Failed to initialize HeartbeatCoordinator (Redis unavailable?)"`
- Features silently disabled
- Workflow execution continues normally
- Methods return empty values (`""`, `None`)

No exceptions raised - workflows remain functional without coordination.

---

## Demo Script

Run the complete demonstration:

```bash
python examples/coordinated_workflow_demo.py
```

**Includes:**
1. Producer-Consumer pattern with coordination
2. Orchestrator pattern with broadcasts
3. Abort signal handling

**Output:**
```
======================================================================
PRODUCER-CONSUMER WORKFLOW DEMONSTRATION
======================================================================

Starting producer and consumer workflows...

[producer] Starting workflow...
[consumer] Starting workflow...
[consumer] Waiting for producer signal...
[producer] Completed generate stage
[producer] Completed validate stage
[producer] Sent task_complete signal to consumer
[consumer] Received signal from producer!
[consumer] Processing data...

======================================================================
RESULTS
======================================================================
Producer: ✅ Success
Consumer: ✅ Success
```

---

## Integration Testing

### Test Heartbeat Integration

```python
import pytest
from attune.workflows.base import BaseWorkflow, ModelTier


class TestWorkflow(BaseWorkflow):
    name = "test-workflow"
    stages = ["stage1"]
    tier_map = {"stage1": ModelTier.CHEAP}

    async def run_stage(self, stage_name: str, tier: ModelTier, input_data: dict):
        return {"result": "success"}, 10, 5


@pytest.mark.asyncio
async def test_workflow_with_heartbeat_tracking():
    """Test workflow with heartbeat tracking enabled."""
    from attune.telemetry import HeartbeatCoordinator

    coordinator = HeartbeatCoordinator()

    # Clear any existing heartbeats
    coordinator._heartbeat_coordinator = None

    workflow = TestWorkflow(
        enable_heartbeat_tracking=True,
        agent_id="test-workflow-001",
    )

    # Execute workflow
    result = await workflow.execute()

    assert result.success

    # Note: Heartbeat will have expired after workflow completion
    # as final status removes the heartbeat from Redis
```

### Test Coordination Integration

```python
@pytest.mark.asyncio
async def test_producer_consumer_coordination():
    """Test coordination between producer and consumer workflows."""
    producer = ProducerWorkflow(
        enable_coordination=True,
        agent_id="producer-test",
    )

    consumer = ConsumerWorkflow(
        enable_coordination=True,
        agent_id="consumer-test",
    )

    # Run concurrently
    producer_task = asyncio.create_task(producer.execute())
    consumer_task = asyncio.create_task(consumer.execute())

    producer_result, consumer_result = await asyncio.gather(
        producer_task, consumer_task
    )

    assert producer_result.success
    assert consumer_result.success
```

---

## State Persistence Integration (v2.5.0)

### StatePersistenceMixin

BaseWorkflow now includes `StatePersistenceMixin` which records workflow lifecycle events when a `state_store` is provided:

```python
from attune.agents.state.store import AgentStateStore
from attune.workflows.base import BaseWorkflow, ModelTier

state_store = AgentStateStore(storage_dir=".attune/agents/state")

workflow = MyWorkflow(
    cost_tracker=cost_tracker,
    state_store=state_store,  # Enables state persistence
)

result = await workflow.execute(input_data)

# State store now contains:
# - Workflow start/complete records
# - Per-stage checkpoints with cost and duration
# - Recovery checkpoints for interrupted workflows
```

**Lifecycle hooks (automatic when state_store is set):**

- `_state_record_workflow_start()` - Called at execution start
- `_state_record_stage_start(stage_name)` - Before each stage
- `_state_record_stage_complete(stage_name, cost, duration_ms, tier)` - After each stage
- `_state_record_workflow_complete(success, total_cost, execution_time_ms, error)` - At completion

All state store calls are wrapped in try/except - persistence errors never crash the workflow.

---

## Multi-Agent Stage Delegation (v2.5.0)

### MultiAgentStageMixin

Workflow stages can delegate to a `DynamicTeam` instead of a single LLM call:

```python
class MyAdvancedWorkflow(BaseWorkflow):
    name = "advanced-review"
    stages = ["triage", "multi_agent_review", "report"]
    tier_map = {
        "triage": ModelTier.CHEAP,
        "multi_agent_review": ModelTier.CAPABLE,
        "report": ModelTier.CHEAP,
    }

    async def run_stage(self, stage_name, tier, input_data):
        if stage_name == "multi_agent_review":
            # Delegate to a team of agents
            return await self._run_multi_agent_stage(
                stage_name=stage_name,
                input_data=input_data,
                team_config={
                    "agents": [
                        {"template_id": "security_auditor"},
                        {"template_id": "code_reviewer"},
                    ],
                    "strategy": "parallel",
                    "quality_gates": {"min_score": 70},
                },
            )
        # ... other stages use single LLM call
```

---

## Workflow Composition (v2.5.0)

### WorkflowComposer

Compose entire workflows into a `DynamicTeam`:

```python
from attune.orchestration import WorkflowComposer

composer = WorkflowComposer(state_store=state_store)
team = composer.compose(
    team_name="comprehensive-review",
    workflows=[
        {"workflow": SecurityAuditWorkflow, "kwargs": {"cost_tracker": ct}},
        {"workflow": CodeReviewWorkflow, "kwargs": {"cost_tracker": ct}},
    ],
    strategy="parallel",
    quality_gates={"min_score": 70},
)

result = await team.execute({"target": "src/"})
```

Each workflow is wrapped via `WorkflowAgentAdapter` which bridges the async/sync boundary and converts `WorkflowResult` to `SDKAgentResult`.

---

## Related Documentation

- [AGENT_TRACKING_AND_COORDINATION.md](./AGENT_TRACKING_AND_COORDINATION.md) - Pattern 1 & 2 detailed docs
- [AGENT_COORDINATION_ARCHITECTURE.md](./AGENT_COORDINATION_ARCHITECTURE.md) - Full architecture (Patterns 1-6)
- [ADAPTIVE_ROUTING_INTEGRATION.md](./ADAPTIVE_ROUTING_INTEGRATION.md) - Pattern 3 integration
- [BaseWorkflow API Reference](../src/attune/workflows/base.py) - Complete workflow API

---

## Next Steps

### Remaining Patterns

**Pattern 6: Real-Time Event Streaming** (not yet implemented)

- Redis Streams + WebSocket for live updates
- Real-time dashboard integration

**Pattern 7: Human Approval Gates** (not yet implemented)

- Pause workflow for human decisions
- Approval signal integration

**Pattern 8: Agent-to-LLM Feedback Loop** (not yet implemented)

- Quality ratings inform routing
- Automatic tier selection based on feedback

---

## FAQ

### Q: Do I need Redis to use workflows?

**A:** No. Redis is only required for heartbeat tracking and coordination. Workflows work normally without Redis - these features just gracefully degrade.

### Q: What happens if Redis crashes during workflow execution?

**A:** Heartbeat updates and signal operations will fail silently (warnings logged). Workflow execution continues normally. When Redis restarts, new workflows will resume using coordination features.

### Q: Can I use heartbeat tracking without coordination?

**A:** Yes. The features are independent:
```python
# Heartbeat only
workflow = MyWorkflow(enable_heartbeat_tracking=True)

# Coordination only
workflow = MyWorkflow(enable_coordination=True)

# Both
workflow = MyWorkflow(enable_heartbeat_tracking=True, enable_coordination=True)
```

### Q: How do I monitor workflows in production?

**A:** Use the CLI commands:
```bash
# View active workflows
attune telemetry agents

# View pending signals for a workflow
attune telemetry signals --agent my-workflow-abc12345
```

Or build a custom dashboard using the Python API from `HeartbeatCoordinator` and `CoordinationSignals`.

---

**Status:** ✅ Ready for Production Use
**Version:** 5.0.0
**Last Updated:** February 10, 2026
**Dependencies:** Redis 5.0+ (optional for heartbeats/signals)
