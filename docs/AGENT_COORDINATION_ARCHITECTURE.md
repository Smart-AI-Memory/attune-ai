---
description: Agent Coordination Architecture - TTL & Telemetry Patterns: System architecture overview with components, data flow, and design decisions. Understand the framework internals.
---

# Agent Coordination Architecture - TTL & Telemetry Patterns

**Version:** 1.0
**Created:** January 27, 2026
**Status:** Architectural Proposal

---

## Executive Summary

This document proposes innovative patterns for using TTL (Time-To-Live) and telemetry to enhance coordination and communication between agents, LLMs, and humans in the Attune AI.

**Key Innovation:** Treat Redis memory as a **communication bus** rather than just storage, using TTL-based keys as ephemeral signals and telemetry as real-time coordination feedback.

**Goals:**
1. **Agent-to-Agent Communication** - Agents coordinate via short-lived Redis keys
2. **Agent-to-Human Communication** - Real-time telemetry feeds human dashboards
3. **Agent-to-LLM Communication** - Telemetry informs model selection and routing
4. **Human-to-Agent Communication** - Humans can inject signals via Redis keys

---

## Current State Analysis

### Existing TTL Strategies

From [memory/types.py:39-56](../src/attune/memory/types.py#L39-L56):

```python
class TTLStrategy(Enum):
    WORKING_RESULTS = 3600      # 1 hour - Workflow outputs
    STAGED_PATTERNS = 86400     # 24 hours - Patterns awaiting validation
    COORDINATION = 300          # 5 minutes - Agent coordination signals
    CONFLICT_CONTEXT = 604800   # 7 days - Conflict resolution context
    SESSION = 1800              # 30 minutes - User session data
    STREAM_ENTRY = 86400 * 7    # 7 days - Audit stream entries
    TASK_QUEUE = 3600 * 4       # 4 hours - Task queue items
```

### Existing Telemetry Capabilities

From [telemetry/usage_tracker.py](../src/attune/telemetry/usage_tracker.py):

- **LLM Call Tracking** - Workflow, stage, tier, model, cost, tokens, duration
- **Cache Statistics** - Hit rates, reads, writes, savings
- **Cost Analysis** - Tier distribution, savings vs baseline
- **Provider Metrics** - Usage by provider (Anthropic, OpenAI, etc.)

### Existing Redis Features

From [memory/short_term.py](../src/attune/memory/short_term.py):

- **Pub/Sub** - Real-time message broadcasting
- **Streams** - Append-only event log (Redis 5.0+)
- **Sorted Sets** - Time-ordered data structures
- **Lists** - Queue data structures
- **Two-Tier Caching** - Local LRU + Redis for fast access

---

## Pattern 1: TTL-Based Agent Heartbeats

**Problem:** How do we know if an agent is still running? Did it hang? Is it making progress?

**Solution:** Agents publish heartbeat keys with short TTL (30-60 seconds). Other agents/humans can check if key exists to verify liveness.

### Implementation

```python
# File: src/attune/orchestration/heartbeat.py

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from attune.memory import RedisShortTermMemory
from attune.memory.types import TTLStrategy

@dataclass
class AgentHeartbeat:
    """Agent heartbeat with status and progress."""
    agent_id: str
    status: str  # "starting", "running", "waiting", "completing"
    progress: float  # 0.0 - 1.0
    current_task: str
    last_beat: datetime
    metadata: dict[str, Any]

class HeartbeatCoordinator:
    """Manages agent heartbeats via TTL-based Redis keys."""

    HEARTBEAT_TTL = 60  # 1 minute
    HEARTBEAT_INTERVAL = 30  # Beat every 30 seconds

    def __init__(self, memory: RedisShortTermMemory):
        self.memory = memory
        self.agent_id = None  # Set when agent starts

    def start_heartbeat(self, agent_id: str, metadata: dict[str, Any]) -> None:
        """Start heartbeat for this agent.

        Args:
            agent_id: Unique agent identifier
            metadata: Initial metadata (workflow, run_id, etc.)
        """
        self.agent_id = agent_id
        self._publish_heartbeat(
            status="starting",
            progress=0.0,
            current_task="initializing",
            metadata=metadata
        )

    def beat(self, status: str, progress: float, current_task: str) -> None:
        """Publish heartbeat update.

        Args:
            status: Current agent status
            progress: Progress percentage (0.0 - 1.0)
            current_task: Human-readable current task description
        """
        if not self.agent_id:
            return

        self._publish_heartbeat(
            status=status,
            progress=progress,
            current_task=current_task,
            metadata={}
        )

    def stop_heartbeat(self, final_status: str = "completed") -> None:
        """Stop heartbeat (agent finished).

        Args:
            final_status: Final status ("completed", "failed", "cancelled")
        """
        if not self.agent_id:
            return

        # Publish final heartbeat with short TTL
        self._publish_heartbeat(
            status=final_status,
            progress=1.0,
            current_task="finished",
            metadata={"final": True}
        )

        # Clear agent ID
        self.agent_id = None

    def _publish_heartbeat(
        self,
        status: str,
        progress: float,
        current_task: str,
        metadata: dict[str, Any]
    ) -> None:
        """Publish heartbeat to Redis with TTL."""
        heartbeat = AgentHeartbeat(
            agent_id=self.agent_id,
            status=status,
            progress=progress,
            current_task=current_task,
            last_beat=datetime.utcnow(),
            metadata=metadata
        )

        # Store in Redis with TTL
        key = f"heartbeat:{self.agent_id}"
        self.memory.stash(
            key=key,
            data=heartbeat.__dict__,
            credentials=None,  # System operation
            ttl_seconds=self.HEARTBEAT_TTL
        )

    def get_active_agents(self) -> list[AgentHeartbeat]:
        """Get all currently active agents.

        Returns:
            List of active agent heartbeats
        """
        # Scan for heartbeat:* keys
        keys = self.memory._keys("heartbeat:*")

        heartbeats = []
        for key in keys:
            data = self.memory.retrieve(key, credentials=None)
            if data:
                heartbeats.append(AgentHeartbeat(**data))

        return heartbeats

    def is_agent_alive(self, agent_id: str) -> bool:
        """Check if agent is still alive.

        Args:
            agent_id: Agent to check

        Returns:
            True if heartbeat key exists (agent is alive)
        """
        key = f"heartbeat:{agent_id}"
        return self.memory.retrieve(key, credentials=None) is not None

    def get_agent_status(self, agent_id: str) -> AgentHeartbeat | None:
        """Get current status of an agent.

        Args:
            agent_id: Agent to query

        Returns:
            AgentHeartbeat or None if agent not active
        """
        key = f"heartbeat:{agent_id}"
        data = self.memory.retrieve(key, credentials=None)

        if data:
            return AgentHeartbeat(**data)
        return None
```

### Usage in Workflows

```python
# In BaseWorkflow or orchestration strategies

class ParallelStrategy(ExecutionStrategy):
    async def execute(self, agents: list[AgentTemplate], context: dict[str, Any]) -> StrategyResult:
        """Execute agents in parallel with heartbeat monitoring."""

        # Initialize heartbeat coordinator
        heartbeat = HeartbeatCoordinator(memory=get_memory())

        async def run_with_heartbeat(agent: AgentTemplate) -> AgentResult:
            """Run agent with heartbeat tracking."""
            agent_id = f"{agent.name}_{uuid.uuid4().hex[:8]}"

            # Start heartbeat
            heartbeat.start_heartbeat(
                agent_id=agent_id,
                metadata={
                    "workflow": context.get("workflow_name"),
                    "run_id": context.get("run_id"),
                    "agent_name": agent.name
                }
            )

            try:
                # Update heartbeat periodically during execution
                heartbeat.beat("running", 0.5, f"Executing {agent.name}")

                result = await self._execute_agent(agent, context)

                # Final heartbeat
                heartbeat.stop_heartbeat("completed")

                return result
            except Exception as e:
                heartbeat.stop_heartbeat("failed")
                raise

        # Execute all agents in parallel with heartbeats
        tasks = [run_with_heartbeat(agent) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return self._aggregate_results(results)
```

### Benefits

1. **Real-time Monitoring** - See which agents are running, stuck, or finished
2. **Automatic Cleanup** - Dead agents' heartbeats expire automatically (TTL)
3. **Debugging** - Identify hung agents before timeout
4. **Human Visibility** - Users can see live agent status

---

## Pattern 2: TTL-Based Agent Coordination Signals

**Problem:** Agents need to coordinate without blocking. Example: Agent A discovers critical issue → needs Agent B to re-run analysis.

**Solution:** Use short-TTL Redis keys as **coordination signals** that expire if not consumed.

### Signal Types

```python
# File: src/attune/orchestration/signals.py

from enum import Enum
from dataclasses import dataclass
from typing import Any

class SignalType(Enum):
    """Types of coordination signals."""
    BLOCKER_DETECTED = "blocker"        # Critical issue requires attention
    ASSISTANCE_NEEDED = "help"          # Agent needs help from another
    APPROVAL_REQUIRED = "approval"      # Human approval needed
    RESULT_READY = "result"             # Result ready for consumption
    CANCEL_REQUESTED = "cancel"         # Request to cancel operation
    PRIORITY_CHANGED = "priority"       # Task priority updated

@dataclass
class CoordinationSignal:
    """Signal for agent coordination."""
    signal_type: SignalType
    from_agent: str
    to_agent: str | None  # None = broadcast
    payload: dict[str, Any]
    timestamp: datetime
    expires_at: datetime

class SignalBus:
    """Pub/Sub coordination signal bus using Redis."""

    SIGNAL_TTL = 300  # 5 minutes (matches TTLStrategy.COORDINATION)

    def __init__(self, memory: RedisShortTermMemory):
        self.memory = memory

    def emit_signal(
        self,
        signal_type: SignalType,
        from_agent: str,
        to_agent: str | None,
        payload: dict[str, Any]
    ) -> str:
        """Emit coordination signal.

        Args:
            signal_type: Type of signal
            from_agent: Sending agent ID
            to_agent: Target agent ID (None for broadcast)
            payload: Signal data

        Returns:
            Signal ID
        """
        signal_id = f"signal:{uuid.uuid4().hex}"
        now = datetime.utcnow()

        signal = CoordinationSignal(
            signal_type=signal_type,
            from_agent=from_agent,
            to_agent=to_agent,
            payload=payload,
            timestamp=now,
            expires_at=now + timedelta(seconds=self.SIGNAL_TTL)
        )

        # Store signal with TTL
        key = signal_id
        self.memory.stash(
            key=key,
            data=signal.__dict__,
            credentials=None,
            ttl_seconds=self.SIGNAL_TTL
        )

        # Also add to agent's signal queue (sorted set by timestamp)
        if to_agent:
            queue_key = f"signals:{to_agent}"
            # Add to sorted set (score = timestamp)
            # Note: This requires adding sorted set support to memory
            self.memory._zadd(queue_key, {signal_id: now.timestamp()})

        return signal_id

    def get_signals(
        self,
        agent_id: str,
        signal_type: SignalType | None = None
    ) -> list[CoordinationSignal]:
        """Get pending signals for an agent.

        Args:
            agent_id: Agent to get signals for
            signal_type: Optional filter by type

        Returns:
            List of pending signals (oldest first)
        """
        queue_key = f"signals:{agent_id}"

        # Get all signal IDs from sorted set
        signal_ids = self.memory._zrange(queue_key, 0, -1)

        signals = []
        for signal_id in signal_ids:
            signal_data = self.memory.retrieve(signal_id, credentials=None)
            if signal_data:
                signal = CoordinationSignal(**signal_data)

                # Filter by type if specified
                if signal_type is None or signal.signal_type == signal_type:
                    signals.append(signal)
            else:
                # Signal expired (TTL), remove from queue
                self.memory._zrem(queue_key, signal_id)

        return signals

    def consume_signal(self, agent_id: str, signal_id: str) -> None:
        """Mark signal as consumed (delete it).

        Args:
            agent_id: Agent consuming signal
            signal_id: Signal to consume
        """
        # Remove from queue
        queue_key = f"signals:{agent_id}"
        self.memory._zrem(queue_key, signal_id)

        # Delete signal
        self.memory._delete(signal_id)
```

### Usage Example: Cross-Agent Communication

```python
# Agent A discovers critical security vulnerability
signal_bus = SignalBus(memory)

signal_bus.emit_signal(
    signal_type=SignalType.BLOCKER_DETECTED,
    from_agent="security-auditor",
    to_agent="release-manager",  # Notify specific agent
    payload={
        "severity": "HIGH",
        "cve": "CVE-2026-12345",
        "file": "auth.py:142",
        "recommendation": "Upgrade dependency before release"
    }
)

# Agent B (release manager) checks for signals
signals = signal_bus.get_signals(
    agent_id="release-manager",
    signal_type=SignalType.BLOCKER_DETECTED
)

for signal in signals:
    if signal.payload["severity"] == "HIGH":
        # Pause release, notify human
        await pause_release_workflow()
        await notify_human(signal.payload)

        # Consume signal
        signal_bus.consume_signal("release-manager", signal.id)
```

### Benefits

1. **Asynchronous Coordination** - No blocking, agents check signals when ready
2. **Automatic Expiration** - Old signals auto-expire (5 min TTL)
3. **Priority Queuing** - Sorted set orders signals by timestamp
4. **Broadcast Support** - Signals can target specific agent or all agents

---

## Pattern 3: Telemetry-Driven Model Selection

**Problem:** How do we know which model tier to use? Current approach uses static task types.

**Solution:** Use **historical telemetry** to learn which models work best for each workflow stage.

### Adaptive Model Router

```python
# File: src/attune/models/adaptive_routing.py

from dataclasses import dataclass
from attune.telemetry import UsageTracker

@dataclass
class ModelPerformance:
    """Performance metrics for a model on a specific task."""
    model_id: str
    tier: str
    success_rate: float
    avg_latency_ms: float
    avg_cost: float
    sample_size: int

class AdaptiveModelRouter:
    """Route tasks to models based on historical performance."""

    def __init__(self, telemetry: UsageTracker):
        self.telemetry = telemetry

    def get_best_model(
        self,
        workflow: str,
        stage: str,
        max_cost: float | None = None,
        max_latency_ms: int | None = None
    ) -> str:
        """Get best model for this workflow/stage based on telemetry.

        Args:
            workflow: Workflow name
            stage: Stage name
            max_cost: Maximum acceptable cost per call
            max_latency_ms: Maximum acceptable latency

        Returns:
            Model ID to use
        """
        # Get recent telemetry for this workflow
        entries = self.telemetry.get_recent_entries(
            limit=1000,
            days=7
        )

        # Filter to this workflow+stage
        relevant = [
            e for e in entries
            if e.get("workflow") == workflow and e.get("stage") == stage
        ]

        if not relevant:
            # No history, use default (cheap tier)
            return "claude-haiku-3.5"

        # Calculate performance by model
        perf_by_model: dict[str, list[dict]] = {}
        for entry in relevant:
            model = entry["model"]
            if model not in perf_by_model:
                perf_by_model[model] = []
            perf_by_model[model].append(entry)

        # Score each model
        scores = []
        for model, entries in perf_by_model.items():
            # Calculate metrics
            total = len(entries)
            successes = sum(1 for e in entries if e.get("success", True))
            success_rate = successes / total

            avg_latency = sum(e.get("duration_ms", 0) for e in entries) / total
            avg_cost = sum(e.get("cost", 0) for e in entries) / total

            # Apply constraints
            if max_cost and avg_cost > max_cost:
                continue
            if max_latency_ms and avg_latency > max_latency_ms:
                continue

            # Score: prioritize success rate, then cost
            score = success_rate * 100 - avg_cost * 10

            scores.append((score, model, ModelPerformance(
                model_id=model,
                tier=entries[0].get("tier", "unknown"),
                success_rate=success_rate,
                avg_latency_ms=avg_latency,
                avg_cost=avg_cost,
                sample_size=total
            )))

        if not scores:
            # All models filtered out, fallback
            return "claude-haiku-3.5"

        # Return best scoring model
        scores.sort(reverse=True)
        return scores[0][1]

    def recommend_tier_upgrade(
        self,
        workflow: str,
        stage: str
    ) -> tuple[bool, str]:
        """Check if tier should be upgraded based on failure rate.

        Args:
            workflow: Workflow name
            stage: Stage name

        Returns:
            (should_upgrade, reason)
        """
        entries = self.telemetry.get_recent_entries(limit=1000, days=7)

        relevant = [
            e for e in entries
            if e.get("workflow") == workflow and e.get("stage") == stage
        ]

        if len(relevant) < 10:
            # Not enough data
            return False, "Insufficient data"

        # Calculate recent failure rate
        recent = relevant[-20:]  # Last 20 calls
        failures = sum(1 for e in recent if not e.get("success", True))
        failure_rate = failures / len(recent)

        if failure_rate > 0.2:  # >20% failure rate
            return True, f"High failure rate: {failure_rate:.1%} in last 20 calls"

        return False, "Performance acceptable"
```

### Integration with Workflow Execution

```python
# In BaseWorkflow

class BaseWorkflow:
    def __init__(self):
        self.adaptive_router = AdaptiveModelRouter(
            telemetry=UsageTracker.get_instance()
        )

    async def _execute_stage(self, stage: WorkflowStage):
        """Execute stage with adaptive model selection."""

        # Check if we should upgrade tier based on past failures
        should_upgrade, reason = self.adaptive_router.recommend_tier_upgrade(
            workflow=self.name,
            stage=stage.name
        )

        if should_upgrade:
            logger.info(f"Upgrading tier for {stage.name}: {reason}")
            stage.tier = ModelTier.CAPABLE  # Upgrade from CHEAP

        # Get best model based on telemetry
        model = self.adaptive_router.get_best_model(
            workflow=self.name,
            stage=stage.name,
            max_cost=stage.max_cost,
            max_latency_ms=stage.max_latency_ms
        )

        # Execute with selected model
        result = await self._call_model(model, stage.prompt)

        return result
```

### Benefits

1. **Self-Improving** - System learns from experience
2. **Cost Optimization** - Uses cheapest model that meets requirements
3. **Failure Reduction** - Automatically upgrades tier when failures occur
4. **Latency Awareness** - Considers response time in selection

---

## Pattern 4: Real-Time Telemetry Dashboard (Human Visibility)

**Problem:** Humans can't see what agents are doing in real-time. Did the workflow start? Is it stuck?

**Solution:** **Redis Streams** for real-time event feed + WebSocket/SSE for browser updates.

### Event Stream Architecture

```python
# File: src/attune/monitoring/event_stream.py

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from attune.memory import RedisShortTermMemory

@dataclass
class WorkflowEvent:
    """Real-time workflow event for streaming."""
    event_id: str
    timestamp: datetime
    event_type: str  # "workflow_started", "stage_completed", "agent_message", etc.
    workflow_name: str
    run_id: str
    agent_id: str | None
    data: dict[str, Any]
    severity: str  # "info", "warning", "error"

class EventStream:
    """Real-time event streaming using Redis Streams."""

    STREAM_KEY = "events:workflows"
    MAX_LEN = 10000  # Keep last 10k events

    def __init__(self, memory: RedisShortTermMemory):
        self.memory = memory

    def publish_event(self, event: WorkflowEvent) -> str:
        """Publish event to stream.

        Args:
            event: Event to publish

        Returns:
            Event ID in stream
        """
        # Add to Redis stream
        event_data = {
            "event_type": event.event_type,
            "workflow_name": event.workflow_name,
            "run_id": event.run_id,
            "agent_id": event.agent_id or "",
            "data": json.dumps(event.data),
            "severity": event.severity,
            "timestamp": event.timestamp.isoformat()
        }

        # XADD with maxlen (trim old events)
        stream_id = self.memory._xadd(
            self.STREAM_KEY,
            event_data,
            maxlen=self.MAX_LEN
        )

        return stream_id

    def read_events(
        self,
        run_id: str | None = None,
        since_id: str = "0",
        count: int = 100
    ) -> list[WorkflowEvent]:
        """Read events from stream.

        Args:
            run_id: Filter by run ID (optional)
            since_id: Start reading after this ID
            count: Max events to return

        Returns:
            List of events
        """
        # XREAD from stream
        raw_events = self.memory._xread(
            {self.STREAM_KEY: since_id},
            count=count
        )

        events = []
        for stream_key, event_list in raw_events:
            for event_id, event_data in event_list:
                # Parse event
                event = WorkflowEvent(
                    event_id=event_id,
                    timestamp=datetime.fromisoformat(event_data["timestamp"]),
                    event_type=event_data["event_type"],
                    workflow_name=event_data["workflow_name"],
                    run_id=event_data["run_id"],
                    agent_id=event_data["agent_id"] or None,
                    data=json.loads(event_data["data"]),
                    severity=event_data["severity"]
                )

                # Filter by run_id if specified
                if run_id is None or event.run_id == run_id:
                    events.append(event)

        return events

    def subscribe_to_workflow(self, run_id: str):
        """Subscribe to events for a specific workflow run.

        Yields events as they occur (blocking iterator).

        Args:
            run_id: Workflow run ID to follow

        Yields:
            WorkflowEvent instances
        """
        last_id = "0"

        while True:
            events = self.read_events(
                run_id=run_id,
                since_id=last_id,
                count=10
            )

            for event in events:
                yield event
                last_id = event.event_id

            # Check if workflow completed
            if events and any(
                e.event_type in ("workflow_completed", "workflow_failed")
                for e in events
            ):
                break

            # Wait before polling again
            time.sleep(0.5)
```

### Workflow Integration

```python
# In BaseWorkflow or orchestration

class BaseWorkflow:
    def __init__(self):
        self.event_stream = EventStream(memory=get_memory())
        self.run_id = str(uuid.uuid4())

    async def execute(self, input_data: dict):
        """Execute workflow with event streaming."""

        # Publish workflow started event
        self.event_stream.publish_event(WorkflowEvent(
            event_id="",  # Auto-generated
            timestamp=datetime.utcnow(),
            event_type="workflow_started",
            workflow_name=self.name,
            run_id=self.run_id,
            agent_id=None,
            data={"input_keys": list(input_data.keys())},
            severity="info"
        ))

        try:
            # Execute stages
            for stage in self.stages:
                # Stage started
                self.event_stream.publish_event(WorkflowEvent(
                    event_id="",
                    timestamp=datetime.utcnow(),
                    event_type="stage_started",
                    workflow_name=self.name,
                    run_id=self.run_id,
                    agent_id=None,
                    data={"stage": stage.name, "tier": stage.tier.value},
                    severity="info"
                ))

                result = await self._execute_stage(stage)

                # Stage completed
                self.event_stream.publish_event(WorkflowEvent(
                    event_id="",
                    timestamp=datetime.utcnow(),
                    event_type="stage_completed",
                    workflow_name=self.name,
                    run_id=self.run_id,
                    agent_id=None,
                    data={
                        "stage": stage.name,
                        "duration_ms": stage.duration_ms,
                        "cost": stage.cost,
                        "tokens": stage.tokens
                    },
                    severity="info"
                ))

            # Workflow completed
            self.event_stream.publish_event(WorkflowEvent(
                event_id="",
                timestamp=datetime.utcnow(),
                event_type="workflow_completed",
                workflow_name=self.name,
                run_id=self.run_id,
                agent_id=None,
                data={"success": True},
                severity="info"
            ))

        except Exception as e:
            # Workflow failed
            self.event_stream.publish_event(WorkflowEvent(
                event_id="",
                timestamp=datetime.utcnow(),
                event_type="workflow_failed",
                workflow_name=self.name,
                run_id=self.run_id,
                agent_id=None,
                data={"error": str(e)},
                severity="error"
            ))
            raise
```

### Real-Time Dashboard (Web UI)

```python
# File: website/app/api/workflows/stream/route.ts

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const runId = searchParams.get('run_id');

  if (!runId) {
    return new Response('Missing run_id', { status: 400 });
  }

  // Set up SSE (Server-Sent Events)
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      // Connect to Redis stream
      const redis = getRedisClient();
      let lastId = '0';

      while (true) {
        // Read new events
        const events = await redis.xread(
          'STREAMS', 'events:workflows', lastId,
          'COUNT', 10
        );

        if (events && events.length > 0) {
          for (const [_, eventList] of events) {
            for (const [eventId, eventData] of eventList) {
              // Filter by run_id
              if (eventData.run_id === runId) {
                // Send to client
                const sseData = `data: ${JSON.stringify(eventData)}\n\n`;
                controller.enqueue(encoder.encode(sseData));

                // Check if workflow completed
                if (eventData.event_type === 'workflow_completed' ||
                    eventData.event_type === 'workflow_failed') {
                  controller.close();
                  return;
                }
              }

              lastId = eventId;
            }
          }
        }

        // Wait before next poll
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
```

### Benefits

1. **Real-Time Visibility** - Humans see workflow progress live
2. **Debugging** - See exactly where workflow is stuck or failing
3. **Audit Trail** - Redis stream persists events (7 days TTL)
4. **Multiple Subscribers** - Many clients can follow same workflow

---

## Pattern 5: Human Intervention via Redis Keys

**Problem:** Workflow needs human approval but we're in CLI (no interactive prompt).

**Solution:** Workflow writes **approval request key** to Redis, human approves via CLI/dashboard, workflow polls for approval.

### Approval Flow

```python
# File: src/attune/orchestration/approval.py

from dataclasses import dataclass
from datetime import datetime, timedelta
from attune.memory import RedisShortTermMemory

@dataclass
class ApprovalRequest:
    """Request for human approval."""
    request_id: str
    workflow_name: str
    run_id: str
    question: str  # What needs approval
    context: dict[str, Any]  # Context for decision
    timeout_seconds: int
    created_at: datetime

@dataclass
class ApprovalResponse:
    """Human's approval decision."""
    request_id: str
    approved: bool
    reason: str
    responded_at: datetime
    responded_by: str  # User ID

class ApprovalGate:
    """Human approval gate using Redis polling."""

    DEFAULT_TIMEOUT = 300  # 5 minutes

    def __init__(self, memory: RedisShortTermMemory):
        self.memory = memory

    def request_approval(
        self,
        workflow_name: str,
        run_id: str,
        question: str,
        context: dict[str, Any],
        timeout_seconds: int = DEFAULT_TIMEOUT
    ) -> bool:
        """Request human approval (blocking).

        Args:
            workflow_name: Workflow requesting approval
            run_id: Run ID
            question: Question to ask human
            context: Context data for decision
            timeout_seconds: How long to wait

        Returns:
            True if approved, False if denied or timeout
        """
        request_id = f"approval:{run_id}:{uuid.uuid4().hex[:8]}"

        # Create request
        request = ApprovalRequest(
            request_id=request_id,
            workflow_name=workflow_name,
            run_id=run_id,
            question=question,
            context=context,
            timeout_seconds=timeout_seconds,
            created_at=datetime.utcnow()
        )

        # Store request with TTL
        self.memory.stash(
            key=request_id,
            data=request.__dict__,
            credentials=None,
            ttl_seconds=timeout_seconds
        )

        # Also publish notification via pub/sub
        self.memory.publish(
            channel="approvals",
            message={
                "type": "approval_requested",
                "request_id": request_id,
                "question": question
            }
        )

        # Poll for response
        response_key = f"{request_id}:response"
        deadline = datetime.utcnow() + timedelta(seconds=timeout_seconds)

        while datetime.utcnow() < deadline:
            # Check for response
            response_data = self.memory.retrieve(response_key, credentials=None)

            if response_data:
                response = ApprovalResponse(**response_data)

                # Cleanup
                self.memory._delete(request_id)
                self.memory._delete(response_key)

                return response.approved

            # Wait before next check
            time.sleep(2)

        # Timeout - cleanup and return False
        self.memory._delete(request_id)
        return False

    def respond_to_approval(
        self,
        request_id: str,
        approved: bool,
        reason: str,
        user_id: str
    ) -> bool:
        """Respond to approval request (called by human).

        Args:
            request_id: Request to respond to
            approved: Approval decision
            reason: Reason for decision
            user_id: User making decision

        Returns:
            True if response recorded successfully
        """
        # Verify request exists
        request_data = self.memory.retrieve(request_id, credentials=None)
        if not request_data:
            return False  # Request expired or doesn't exist

        # Create response
        response = ApprovalResponse(
            request_id=request_id,
            approved=approved,
            reason=reason,
            responded_at=datetime.utcnow(),
            responded_by=user_id
        )

        # Store response (short TTL, just for polling workflow)
        response_key = f"{request_id}:response"
        self.memory.stash(
            key=response_key,
            data=response.__dict__,
            credentials=None,
            ttl_seconds=60  # 1 minute (workflow will consume quickly)
        )

        return True

    def list_pending_approvals(self) -> list[ApprovalRequest]:
        """List all pending approval requests.

        Returns:
            List of pending requests
        """
        # Scan for approval:* keys
        keys = self.memory._keys("approval:*")

        requests = []
        for key in keys:
            if ":response" in key:
                continue  # Skip response keys

            data = self.memory.retrieve(key, credentials=None)
            if data:
                requests.append(ApprovalRequest(**data))

        return requests
```

### CLI Command for Approval

```bash
# User lists pending approvals
attune approvals list

# Output:
# Pending Approvals:
# 1. [release-workflow] Deploy to production?
#    Context: 127 tests passing, no security issues
#    Timeout: 4m 23s remaining
#    ID: approval:abc123:def456
#
# 2. [code-review] Merge PR #142?
#    Context: 3 files changed, +145 -32 lines
#    Timeout: 2m 10s remaining
#    ID: approval:xyz789:ghi012

# User approves
attune approvals respond approval:abc123:def456 --approve --reason "Tests look good"

# User denies
attune approvals respond approval:xyz789:ghi012 --deny --reason "Need more tests"
```

### Usage in Workflow

```python
# In release workflow

async def execute(self, input_data: dict):
    # ... run tests, security audit, etc.

    # Gate: require human approval before deploy
    approval_gate = ApprovalGate(memory=get_memory())

    approved = approval_gate.request_approval(
        workflow_name=self.name,
        run_id=self.run_id,
        question="Deploy to production?",
        context={
            "tests_passing": 127,
            "security_issues": 0,
            "version": "4.9.1"
        },
        timeout_seconds=300  # 5 minutes
    )

    if not approved:
        raise WorkflowError("Deployment denied by user or timeout")

    # Proceed with deployment
    await self._deploy_to_production()
```

### Benefits

1. **Non-Blocking Approval** - Workflow waits, human responds when ready
2. **Timeout Handling** - Auto-deny after timeout
3. **Audit Trail** - All approval decisions logged
4. **CLI + Dashboard** - Approve via command line or web UI

---

## Pattern 6: Agent-to-LLM Feedback Loop

**Problem:** LLM doesn't know if its output was good or bad. No learning signal.

**Solution:** **Telemetry-based feedback** where agents rate LLM responses, informing future routing.

### Feedback System

```python
# File: src/attune/models/feedback.py

from dataclasses import dataclass
from enum import Enum

class FeedbackType(Enum):
    """Type of feedback."""
    SUCCESS = "success"       # Output met requirements
    FAILURE = "failure"       # Output failed to meet requirements
    RETRY_SUCCEEDED = "retry" # Failed first try, succeeded on retry
    HALLUCINATION = "hallucination"  # Output contained false info
    FORMATTING_ERROR = "format"      # Output format incorrect

@dataclass
class LLMFeedback:
    """Feedback on LLM response quality."""
    call_id: str  # Correlates to LLMCallRecord
    feedback_type: FeedbackType
    rating: float  # 0.0 - 1.0
    details: str
    provided_by: str  # Agent ID or human user
    timestamp: datetime

class FeedbackCollector:
    """Collect feedback on LLM responses."""

    def __init__(self, memory: RedisShortTermMemory):
        self.memory = memory

    def record_feedback(self, feedback: LLMFeedback) -> None:
        """Record feedback for an LLM call.

        Args:
            feedback: Feedback to record
        """
        # Store in Redis sorted set (score = timestamp)
        key = f"feedback:{feedback.call_id}"
        self.memory.stash(
            key=key,
            data=feedback.__dict__,
            credentials=None,
            ttl_seconds=86400 * 30  # 30 days
        )

        # Also update telemetry with feedback
        self._update_telemetry(feedback)

    def get_model_quality_score(
        self,
        model_id: str,
        workflow: str,
        days: int = 7
    ) -> float:
        """Get quality score for a model on a workflow.

        Args:
            model_id: Model to evaluate
            workflow: Workflow name
            days: Days of history to consider

        Returns:
            Quality score 0.0 - 1.0
        """
        # Get all feedback for this model/workflow
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Scan feedback keys
        # (In production, use sorted set for efficient range queries)
        feedback_scores = []

        # Calculate weighted score
        # - Success: 1.0
        # - Retry: 0.7 (worked eventually)
        # - Format error: 0.5 (content ok, format bad)
        # - Failure: 0.2
        # - Hallucination: 0.0 (worst case)

        if not feedback_scores:
            return 0.8  # Default: assume good quality

        return sum(feedback_scores) / len(feedback_scores)
```

### Integration with Workflows

```python
# In BaseWorkflow

async def _execute_stage_with_feedback(self, stage: WorkflowStage):
    """Execute stage and collect feedback on response quality."""

    call_id = str(uuid.uuid4())
    feedback_collector = FeedbackCollector(memory=get_memory())

    # Execute LLM call
    result = await self._call_model(
        model=stage.model,
        prompt=stage.prompt,
        call_id=call_id
    )

    # Validate output
    is_valid, validation_error = self._validate_output(
        result.output,
        expected_format=stage.expected_format
    )

    # Record feedback
    if is_valid:
        feedback_collector.record_feedback(LLMFeedback(
            call_id=call_id,
            feedback_type=FeedbackType.SUCCESS,
            rating=1.0,
            details="Output met requirements",
            provided_by=f"workflow:{self.name}",
            timestamp=datetime.utcnow()
        ))
    else:
        feedback_collector.record_feedback(LLMFeedback(
            call_id=call_id,
            feedback_type=FeedbackType.FORMATTING_ERROR,
            rating=0.5,
            details=validation_error,
            provided_by=f"workflow:{self.name}",
            timestamp=datetime.utcnow()
        ))

        # Retry with upgraded tier
        result = await self._retry_with_better_model(stage)

    return result
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Implement HeartbeatCoordinator
- [ ] Add sorted set support to RedisShortTermMemory
- [ ] Implement SignalBus for coordination
- [ ] Add basic event streaming

### Phase 2: Telemetry Integration (Week 2)
- [ ] Implement AdaptiveModelRouter
- [ ] Add feedback collection system
- [ ] Integrate telemetry-driven routing into BaseWorkflow

### Phase 3: Human Interfaces (Week 3)
- [ ] Implement ApprovalGate
- [ ] Add CLI commands for approvals
- [ ] Build real-time dashboard with SSE

### Phase 4: Testing & Refinement (Week 4)
- [ ] End-to-end testing of all patterns
- [ ] Performance benchmarking
- [ ] Documentation and examples

---

## Performance Considerations

### Redis Load

**With these patterns, Redis will handle:**
- **Heartbeats:** ~100 writes/min (10 agents × 10 beats/min)
- **Signals:** ~50 writes/min (occasional coordination)
- **Events:** ~200 writes/min (workflows + stages)
- **Approvals:** ~10 writes/min (rare)

**Total:** ~360 operations/min = **6 ops/sec** (very low load)

**Redis can handle:** 100,000+ ops/sec

**Conclusion:** These patterns add negligible load to Redis.

### Network Latency

- **Heartbeat checks:** 1ms (local cache hit)
- **Signal polling:** 37ms (Redis network call)
- **Event streaming:** Continuous connection, <10ms per event
- **Approval polling:** 2-second intervals

### Memory Usage

- **Heartbeats:** 100 agents × 200 bytes = 20KB
- **Signals:** 1000 pending × 500 bytes = 500KB
- **Events:** 10,000 events × 1KB = 10MB
- **Approvals:** 10 pending × 1KB = 10KB

**Total:** ~11MB (negligible for modern systems)

---

## Security Considerations

1. **TTL-Based Cleanup** - No manual cleanup needed, expired keys auto-delete
2. **No eval() Usage** - All predicates are JSON data structures
3. **Authentication** - Use AgentCredentials for access control
4. **Rate Limiting** - Limit signal/event publishing per agent
5. **Input Validation** - Validate all Redis key names and data

---

## Questions for Discussion

1. **Do you want Redis pub/sub for real-time notifications?**
   - Alternative: polling with short intervals

2. **Should approval requests support multiple approvers?**
   - Example: "2 out of 3 admins must approve"

3. **What metrics should trigger automatic tier upgrades?**
   - Current: >20% failure rate
   - Other ideas: high latency, hallucination detection

4. **Do you want webhooks for event streaming?**
   - POST events to external URL (Slack, Discord, etc.)

---

## Next Steps

Please review this architecture proposal and let me know:

1. Which patterns are highest priority?
2. Are there use cases I missed?
3. Should I proceed with implementation (start with Phase 1)?

The patterns are designed to be **incrementally adoptable** - you can implement one pattern at a time without breaking existing functionality.
