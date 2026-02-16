---
description: Attune AI - User API Documentation API reference: **Version:** 5.1.0 **Last Updated:** January 27, 2026 **Status:** Anthropic-Native (Claude-only) ---
---

# Attune AI - User API Documentation

**Version:** 5.1.0
**Last Updated:** January 27, 2026
**Status:** Anthropic-Native (Claude-only)

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core APIs](#core-apis)
3. [Workflows](#workflows)
4. [Telemetry & Monitoring](#telemetry--monitoring)
5. [Cost Optimization](#cost-optimization)
6. [CLI Reference](#cli-reference)
7. [Configuration](#configuration)
8. [Examples](#examples)

---

## Quick Start

### Installation

```bash
pip install attune-ai
```

### Basic Usage

```python
from attune.workflows import CodeReviewWorkflow

# Create workflow instance
workflow = CodeReviewWorkflow()

# Execute asynchronously
result = await workflow.execute({
    "path": "./src",
    "files": ["main.py", "utils.py"]
})

print(f"Review complete: {result['status']}")
print(f"Cost: ${result['cost']:.4f}")
```

---

## Core APIs

### 1. Workflows

Base class for all workflows with multi-tier LLM routing.

#### BaseWorkflow

```python
from attune.workflows.base import BaseWorkflow, ModelTier

class CustomWorkflow(BaseWorkflow):
    """Custom workflow with adaptive routing."""

    name = "custom-workflow"
    stages = ["preparation", "analysis", "synthesis"]

    def __init__(self, enable_adaptive_routing: bool = True):
        super().__init__(
            enable_heartbeat_tracking=True,
            enable_adaptive_routing=enable_adaptive_routing
        )

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: dict
    ) -> tuple[dict, int, int]:
        """Execute a workflow stage.

        Args:
            stage_name: Name of the stage
            tier: Model tier (CHEAP, CAPABLE, PREMIUM)
            input_data: Input data for the stage

        Returns:
            Tuple of (result_dict, tokens_in, tokens_out)
        """
        # Your stage logic here
        system_prompt = f"You are executing: {stage_name}"
        user_message = f"Process: {input_data}"

        response = await self._call_llm(
            tier=tier,
            system=system_prompt,
            user_message=user_message
        )

        return response, tokens_in, tokens_out
```

**Key Methods:**

| Method | Description | Returns |
|--------|-------------|---------|
| `execute(input_data: dict)` | Execute workflow | `dict` with status, cost, tokens |
| `get_tier_for_stage(stage: str)` | Get tier for stage | `ModelTier` enum |
| `_call_llm(tier, system, user_message)` | Call LLM with tier | LLM response |

**Model Tiers:**

```python
from attune.workflows.base import ModelTier

ModelTier.CHEAP      # claude-3-5-haiku-20241022 (~$0.001/call)
ModelTier.CAPABLE    # claude-sonnet-4-5 (~$0.008/call)
ModelTier.PREMIUM    # claude-opus-4-5 (~$0.070/call)
```

---

### 2. Telemetry & Usage Tracking

Track LLM usage, costs, and performance metrics.

#### UsageTracker

```python
from attune.telemetry import UsageTracker

# Get singleton instance
tracker = UsageTracker.get_instance()

# Track LLM call
tracker.track_llm_call(
    workflow="code-review",
    stage="analysis",
    tier="CHEAP",
    model="claude-3-5-haiku-20241022",
    provider="anthropic",
    cost=0.0016,
    tokens={"input": 1000, "output": 500},
    cache_hit=True,
    cache_type="prompt",
    duration_ms=1200,
    success=True
)

# Get statistics
stats = tracker.get_stats(days=7)

print(f"Total calls: {stats['total_calls']:,}")
print(f"Total cost: ${stats['total_cost']:.2f}")
print(f"Cache hit rate: {stats['cache_hit_rate']:.1f}%")
print(f"Avg cost per call: ${stats['avg_cost_per_call']:.4f}")

# Get recent entries
entries = tracker.get_recent_entries(limit=100, days=7)
for entry in entries:
    print(f"[{entry['timestamp']}] {entry['workflow']}: ${entry['cost']:.4f}")
```

**Key Methods:**

| Method | Description | Returns |
|--------|-------------|---------|
| `track_llm_call(**kwargs)` | Record LLM API call | `None` |
| `get_stats(days: int)` | Get aggregate statistics | `dict` |
| `get_recent_entries(limit, days)` | Get recent entries | `list[dict]` |
| `export_to_csv(filepath)` | Export to CSV | `None` |

---

### 3. Adaptive Model Routing

Automatically select optimal model based on historical performance.

#### AdaptiveModelRouter

```python
from attune.models import AdaptiveModelRouter
from attune.telemetry import UsageTracker

# Initialize router
tracker = UsageTracker.get_instance()
router = AdaptiveModelRouter(telemetry=tracker)

# Get best model for workflow/stage
model = router.get_best_model(
    workflow="code-review",
    stage="analysis",
    max_cost=0.01,           # Max $0.01 per call
    max_latency_ms=5000,     # Max 5s latency
    min_success_rate=0.9     # Min 90% success
)

print(f"Using: {model}")  # claude-3-5-haiku-20241022

# Check for tier upgrade recommendation
should_upgrade, reason = router.recommend_tier_upgrade(
    workflow="code-review",
    stage="analysis"
)

if should_upgrade:
    print(f"⚠️ Upgrade recommended: {reason}")
    # Upgrade from CHEAP → CAPABLE → PREMIUM
```

**Key Methods:**

| Method | Description | Returns |
|--------|-------------|---------|
| `get_best_model(workflow, stage, ...)` | Get optimal model | `str` (model ID) |
| `recommend_tier_upgrade(workflow, stage)` | Check if upgrade needed | `(bool, str)` |
| `get_routing_stats(workflow, days)` | Get routing statistics | `dict` |

**Decision Logic:**
- **Quality Score:** `(success_rate × 100) - (cost × 10)`
- **Upgrade Trigger:** Failure rate > 20% in last 20 calls
- **Downgrade Consideration:** Success rate > 90% with high cost

---

## Workflows

### Built-in Workflows

#### 1. Code Review Workflow

```python
from attune.workflows import CodeReviewWorkflow

workflow = CodeReviewWorkflow()

result = await workflow.execute({
    "path": "./src",
    "files": ["main.py", "utils.py"],
    "focus_areas": ["security", "performance"]
})

# Output
{
    "status": "success",
    "issues": [
        {"file": "main.py", "line": 42, "severity": "high", "issue": "SQL injection risk"},
        {"file": "utils.py", "line": 15, "severity": "medium", "issue": "Inefficient loop"}
    ],
    "suggestions": [...],
    "cost": 0.0234,
    "tokens": {"input": 15000, "output": 3000}
}
```

#### 2. Test Generation Workflow

```python
from attune.workflows import TestGenerationWorkflow

workflow = TestGenerationWorkflow()

result = await workflow.execute({
    "source_file": "./src/utils.py",
    "functions": ["parse_config", "validate_input"],
    "framework": "pytest"
})

# Output
{
    "status": "success",
    "test_file": "./tests/test_utils.py",
    "tests_generated": 12,
    "coverage_estimate": 0.85,
    "cost": 0.0189
}
```

#### 3. Batch Processing Workflow (50% Cost Savings)

```python
from attune.workflows.batch_processing import (
    BatchProcessingWorkflow,
    BatchRequest
)

workflow = BatchProcessingWorkflow()

# Create batch requests
requests = [
    BatchRequest(
        task_id="task_1",
        task_type="analyze_logs",
        input_data={"logs": "ERROR: Connection failed..."},
        model_tier="capable"
    ),
    BatchRequest(
        task_id="task_2",
        task_type="generate_report",
        input_data={"data": {...}},
        model_tier="cheap"
    )
]

# Execute batch (processes within 24 hours at 50% cost)
results = await workflow.execute_batch(
    requests=requests,
    poll_interval=300,    # Check every 5 minutes
    timeout=86400         # 24 hour max wait
)

# Check results
for result in results:
    if result.success:
        print(f"✓ {result.task_id}: {result.output['content']}")
    else:
        print(f"✗ {result.task_id}: {result.error}")
```

---

## Telemetry & Monitoring

### Agent Tracking

Track agent lifecycle and heartbeats.

```python
from attune.telemetry import HeartbeatCoordinator

# Initialize coordinator
coordinator = HeartbeatCoordinator(
    enable_streaming=True  # Enable real-time event streaming
)

# Start heartbeat for agent
coordinator.start_heartbeat(
    agent_id="my-agent-001",
    metadata={
        "workflow": "code-review",
        "run_id": "abc123"
    }
)

# Update status
coordinator.beat(
    status="running",
    progress=0.5,
    current_stage="analysis"
)

# Complete
coordinator.complete(
    status="success",
    final_state={"issues_found": 3}
)
```

### Inter-Agent Coordination

Send signals between agents.

```python
from attune.telemetry import CoordinationSignals

# Initialize signals
signals = CoordinationSignals(
    agent_id="orchestrator",
    enable_streaming=True
)

# Send signal to specific agent
signals.signal(
    signal_type="task_assigned",
    target_agent="worker-1",
    payload={"task_id": "t123", "priority": "high"}
)

# Broadcast to all agents
signals.broadcast(
    signal_type="shutdown_requested",
    payload={"reason": "maintenance"}
)

# Listen for signals
received = signals.get_signals(
    target_agent="worker-1",
    signal_types=["task_assigned"],
    since=datetime.now() - timedelta(minutes=5)
)
```

### Event Streaming

Real-time event streaming with Redis Streams.

```python
from attune.telemetry import EventStreamer

streamer = EventStreamer()

# Publish event
event_id = streamer.publish_event(
    event_type="workflow_progress",
    data={
        "workflow": "code-review",
        "stage": "analysis",
        "progress": 0.75
    }
)

# Consume events (blocking iterator)
for event in streamer.consume_events(
    event_types=["agent_heartbeat", "workflow_progress"],
    block_ms=5000,    # 5 second timeout
    count=10          # Max 10 events per batch
):
    print(f"[{event.timestamp}] {event.event_type}: {event.data}")

# Get recent events (non-blocking)
recent = streamer.get_recent_events(
    event_type="workflow_progress",
    count=100
)
```

### Human Approval Gates

Pause workflow execution for human approval.

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

# In UI: Respond to approval
ui_gate = ApprovalGate()
pending = ui_gate.get_pending_approvals()

for request in pending:
    # Display to user, get decision
    ui_gate.respond_to_approval(
        request_id=request.request_id,
        approved=True,
        responder="user@example.com",
        reason="Looks good to deploy"
    )
```

### Feedback Loop

Record quality ratings to improve model selection.

```python
from attune.telemetry import FeedbackLoop

feedback = FeedbackLoop()

# Record quality feedback (0.0 = bad, 1.0 = excellent)
feedback.record_feedback(
    workflow_name="code-review",
    stage_name="analysis",
    tier="cheap",
    quality_score=0.85,
    metadata={
        "tokens": 1500,
        "latency_ms": 1200
    }
)

# Get tier recommendation based on history
recommendation = feedback.recommend_tier(
    workflow_name="code-review",
    stage_name="analysis",
    current_tier="cheap"
)

if recommendation.recommended_tier != recommendation.current_tier:
    print(f"Upgrade: {recommendation.current_tier} → {recommendation.recommended_tier}")
    print(f"Reason: {recommendation.reason}")
    print(f"Confidence: {recommendation.confidence:.1%}")

# Get quality statistics
stats = feedback.get_quality_stats(
    workflow_name="code-review",
    stage_name="analysis",
    tier="cheap"
)

print(f"Average quality: {stats.avg_quality:.2f}")
print(f"Sample count: {stats.sample_count}")
print(f"Trend: {'📈' if stats.recent_trend > 0 else '📉'}")
```

---

## Cost Optimization

### 1. Prompt Caching (20-30% Savings)

Automatically enabled for all LLM calls. Track cache performance:

```bash
# CLI: View cache statistics
attune cache stats

# Python API
from attune.telemetry import UsageTracker

tracker = UsageTracker.get_instance()
stats = tracker.get_stats(days=7)

cache_hit_rate = stats['cache_hit_rate']
savings = stats['cache_savings']

print(f"Cache hit rate: {cache_hit_rate:.1f}%")
print(f"Cost savings: ${savings:.2f}")
```

### 2. Batch API (50% Savings)

Submit non-urgent tasks for asynchronous processing:

```bash
# CLI: Submit batch
attune batch submit requests.json

# CLI: Check status
attune batch status msgbatch_abc123

# CLI: Get results
attune batch results msgbatch_abc123 output.json

# CLI: Wait for completion
attune batch wait msgbatch_abc123 output.json --poll-interval 300
```

### 3. Adaptive Routing ($2,000/year Potential Savings)

Automatically uses cheapest model that meets quality requirements:

```python
# Enable in workflow
workflow = CodeReviewWorkflow(enable_adaptive_routing=True)

# Or manually check recommendations
from attune.models import AdaptiveModelRouter
from attune.telemetry import UsageTracker

router = AdaptiveModelRouter(UsageTracker.get_instance())
model = router.get_best_model(
    workflow="code-review",
    stage="analysis",
    max_cost=0.01
)
```

### 4. Precise Token Counting (>98% Accuracy)

Accurate cost estimation before API calls:

```python
from attune_llm.providers import AnthropicProvider

provider = AnthropicProvider()

# Estimate tokens
messages = [{"role": "user", "content": "Hello, world!"}]
tokens = provider.estimate_tokens(messages)

print(f"Estimated tokens: {tokens}")

# Calculate cost
cost = provider.calculate_actual_cost(
    input_tokens=tokens,
    output_tokens=500,
    cache_creation_tokens=0,
    cache_read_tokens=1000
)

print(f"Estimated cost: ${cost:.4f}")
```

---

## CLI Reference

### Workflow Commands

```bash
# List available workflows
attune workflow list

# Run workflow
attune workflow run code-review --input '{"path": "./src"}'

# Run with JSON output
attune workflow run bug-predict --json
```

### Telemetry Commands

```bash
# Show usage statistics
attune telemetry show --limit 100

# Export to CSV
attune telemetry export output.csv --format csv

# Reset telemetry data
attune telemetry reset
```

### Batch Processing Commands

```bash
# Submit batch job
attune batch submit requests.json

# Check batch status
attune batch status msgbatch_abc123 [--json]

# Get batch results
attune batch results msgbatch_abc123 output.json

# Wait for completion
attune batch wait msgbatch_abc123 output.json --poll-interval 300 --timeout 86400
```

### Cache Commands

```bash
# View cache statistics
attune cache stats [--verbose] [--json]
```

### Routing Commands

```bash
# View routing statistics
attune routing stats code-review [--stage analysis] [--days 7]

# Check tier upgrade recommendations
attune routing check code-review [--stage analysis]
attune routing check --all

# Compare model performance
attune routing models --provider anthropic [--days 30]
```

---

## Configuration

### Environment Variables

```bash
# Required
export ANTHROPIC_API_KEY="your-api-key-here"

# Optional
export ATTUNE_LOG_LEVEL="INFO"            # DEBUG, INFO, WARNING, ERROR
export ATTUNE_CACHE_DIR="~/.empathy"      # Cache directory
export ATTUNE_REDIS_URL="redis://localhost:6379"  # Redis connection
```

### Configuration File

Create `empathy.config.yml`:

```yaml
# Provider settings
provider: anthropic
api_key: ${ANTHROPIC_API_KEY}

# Model tier defaults
tier_defaults:
  cheap: claude-3-5-haiku-20241022
  capable: claude-sonnet-4-5
  premium: claude-opus-4-5

# Telemetry settings
telemetry:
  enabled: true
  retention_days: 30
  export_format: csv

# Adaptive routing
adaptive_routing:
  enabled: true
  min_samples: 10
  quality_threshold: 0.7
  failure_rate_threshold: 0.2

# Batch processing
batch:
  poll_interval: 300        # 5 minutes
  timeout: 86400            # 24 hours

# Redis (optional)
redis:
  url: redis://localhost:6379
  enabled: false
```

Load configuration:

```python
from attune.config import load_config

config = load_config("empathy.config.yml")
```

---

## Examples

### Example 1: Cost-Optimized Code Review

```python
import asyncio
from attune.workflows import CodeReviewWorkflow
from attune.telemetry import UsageTracker

async def review_codebase():
    """Review codebase with cost optimization."""

    # Enable adaptive routing for cost optimization
    workflow = CodeReviewWorkflow(
        enable_adaptive_routing=True,
        enable_heartbeat_tracking=True
    )

    # Execute review
    result = await workflow.execute({
        "path": "./src",
        "focus_areas": ["security", "performance"]
    })

    # Show results and cost
    print(f"\n✓ Review complete")
    print(f"  Issues found: {len(result['issues'])}")
    print(f"  Cost: ${result['cost']:.4f}")
    print(f"  Tokens: {result['tokens']['total']:,}")

    # Show cost savings
    tracker = UsageTracker.get_instance()
    stats = tracker.get_stats(days=1)

    print(f"\n💰 Cost Optimization")
    print(f"  Cache hit rate: {stats['cache_hit_rate']:.1f}%")
    print(f"  Cache savings: ${stats['cache_savings']:.4f}")
    print(f"  Total cost: ${stats['total_cost']:.4f}")

if __name__ == "__main__":
    asyncio.run(review_codebase())
```

### Example 2: Batch Log Analysis (50% Cheaper)

```python
import asyncio
from attune.workflows.batch_processing import (
    BatchProcessingWorkflow,
    BatchRequest
)

async def analyze_logs_batch():
    """Analyze logs in batch for 50% cost savings."""

    workflow = BatchProcessingWorkflow()

    # Create batch requests from log files
    requests = []
    for i, log_file in enumerate(["app.log", "error.log", "access.log"]):
        with open(log_file) as f:
            logs = f.read()

        requests.append(BatchRequest(
            task_id=f"log_{i}",
            task_type="analyze_logs",
            input_data={"logs": logs},
            model_tier="cheap"  # Use cheapest tier for bulk analysis
        ))

    print(f"📤 Submitting {len(requests)} log analysis tasks...")

    # Execute batch (50% cheaper, processes within 24 hours)
    results = await workflow.execute_batch(
        requests=requests,
        poll_interval=300,    # Check every 5 minutes
        timeout=3600          # 1 hour timeout
    )

    # Process results
    success_count = sum(1 for r in results if r.success)
    print(f"\n✓ Batch complete: {success_count}/{len(results)} successful")

    for result in results:
        if result.success:
            print(f"\n{result.task_id}:")
            print(f"  Issues: {result.output['content']}")
        else:
            print(f"\n{result.task_id}: ✗ {result.error}")

if __name__ == "__main__":
    asyncio.run(analyze_logs_batch())
```

### Example 3: Real-Time Dashboard

```python
from attune.telemetry import EventStreamer, HeartbeatCoordinator
import asyncio

async def dashboard_monitor():
    """Monitor agent activity in real-time."""

    streamer = EventStreamer()

    print("📊 Real-Time Agent Dashboard")
    print("=" * 50)

    # Consume events in real-time
    for event in streamer.consume_events(
        event_types=["agent_heartbeat", "coordination_signal"],
        block_ms=5000  # 5 second timeout
    ):
        # Display event
        if event.event_type == "agent_heartbeat":
            data = event.data
            agent_id = data.get("agent_id", "unknown")
            status = data.get("status", "unknown")
            progress = data.get("progress", 0) * 100

            print(f"[{event.timestamp}] Agent {agent_id}: {status} ({progress:.0f}%)")

        elif event.event_type == "coordination_signal":
            data = event.data
            signal = data.get("signal_type", "unknown")
            target = data.get("target_agent", "all")

            print(f"[{event.timestamp}] Signal: {signal} → {target}")

if __name__ == "__main__":
    asyncio.run(dashboard_monitor())
```

---

## API Reference

For complete API reference, see:

- [Workflows API](./workflows.md)
- [Telemetry API](./telemetry.md)
- [Models API](./models.md)
- [CLI Reference](./cli.md)

---

## Support

- **Documentation:** https://attune-ai.vercel.app
- **GitHub:** https://github.com/Smart-AI-Memory/attune-ai
- **Issues:** https://github.com/Smart-AI-Memory/attune-ai/issues
- **Discussions:** https://github.com/Smart-AI-Memory/attune-ai/discussions

---

**Last Updated:** January 27, 2026
**Framework Version:** 5.1.0
**License:** Apache License 2.0 0.9
