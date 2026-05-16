---
type: reference
name: telemetry-reference
feature: telemetry
depth: reference
generated_at: 2026-05-16T06:19:45.831550+00:00
source_hash: ed8485991002cc1c218f69b4f33f230bcbdc4325599a2e03f2bbe584d94a5e90
status: generated
---

# Telemetry reference

Track usage, coordinate agents, manage approval gates, and collect quality feedback.

## Classes

| Class | Description | File |
|-------|-------------|------|
| `CoordinationSignal` | Coordination signal between agents. | `src/attune/telemetry/agent_coordination.py` |
| `CoordinationSignals` | TTL-based inter-agent coordination signals. | `src/attune/telemetry/agent_coordination.py` |
| `AgentHeartbeat` | Agent heartbeat data structure. | `src/attune/telemetry/agent_tracking.py` |
| `HeartbeatCoordinator` | Coordinates agent heartbeats using Redis TTL keys. | `src/attune/telemetry/agent_tracking.py` |
| `ApprovalRequest` | Approval request with context for human decision. | `src/attune/telemetry/approval_gates.py` |
| `ApprovalResponse` | Response to an approval request. | `src/attune/telemetry/approval_gates.py` |
| `ApprovalGate` | Human approval gates for workflow control. | `src/attune/telemetry/approval_gates.py` |
| `StreamEvent` | Event published to Redis Stream. | `src/attune/telemetry/event_streaming.py` |
| `EventStreamer` | Real-time event streaming using Redis Streams. | `src/attune/telemetry/event_streaming.py` |
| `FeatureStatus` | Status of an optional feature. | `src/attune/telemetry/features.py` |
| `FeatureInfo` | Information about a telemetry feature. | `src/attune/telemetry/features.py` |
| `TelemetryFeatures` | Check availability of telemetry features. | `src/attune/telemetry/features.py` |
| `FeedbackLoop` | Agent-to-LLM feedback loop for quality-based learning. | `src/attune/telemetry/feedback_loop.py` |
| `ModelTier` | Model tier enum matching workflows.base.ModelTier. | `src/attune/telemetry/feedback_models.py` |
| `FeedbackEntry` | Quality feedback for an LLM response. | `src/attune/telemetry/feedback_models.py` |
| `QualityStats` | Quality statistics for a workflow stage. | `src/attune/telemetry/feedback_models.py` |
| `TierRecommendation` | Tier recommendation based on quality feedback. | `src/attune/telemetry/feedback_models.py` |
| `HelpTracker` | Append-only JSONL tracker for help-system queries. | `src/attune/telemetry/help_tracker.py` |
| `UsageTracker` | Privacy-first local telemetry tracker. | `src/attune/telemetry/usage_tracker.py` |

### CoordinationSignal

Dataclass representing a coordination signal passed between agents.

| Field | Type | Default |
|-------|------|---------|
| `signal_id` | `str` | — |
| `signal_type` | `str` | — |
| `source_agent` | `str` | — |
| `target_agent` | `str | None` | — |
| `payload` | `dict[str, Any]` | — |
| `timestamp` | `datetime` | — |
| `ttl_seconds` | `int` | `60` |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | `self` | `dict[str, Any]` | Serialize to a dictionary. |
| `from_dict` | `cls, data: dict[str, Any]` | `CoordinationSignal` | Deserialize from a dictionary. |

### CoordinationSignals

TTL-based inter-agent coordination signals backed by Redis.

#### Constructor

| Parameter | Type | Default |
|-----------|------|---------|
| `memory` | — | — |
| `agent_id` | `str | None` | `None` |
| `enable_streaming` | `bool` | `False` |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `signal` | `self, signal_type: str, source_agent: str \| None = None, target_agent: str \| None = None, payload: dict[str, Any] \| None = None, ttl_seconds: int \| None = None, credentials: AgentCredentials \| None = None` | `str` | Send a directed signal to a target agent. |
| `broadcast` | `self, signal_type: str, source_agent: str \| None = None, payload: dict[str, Any] \| None = None, ttl_seconds: int \| None = None, credentials: AgentCredentials \| None = None` | `str` | Broadcast a signal to all agents. |
| `wait_for_signal` | `self, signal_type: str, source_agent: str \| None = None, timeout: float = 30.0, poll_interval: float = 0.5` | `CoordinationSignal \| None` | Block until a matching signal arrives or the timeout elapses. |
| `check_signal` | `self, signal_type: str, source_agent: str \| None = None, consume: bool = True` | `CoordinationSignal \| None` | Non-blocking check for a pending signal. |
| `get_pending_signals` | `self, signal_type: str \| None = None` | `list[CoordinationSignal]` | Return all pending signals, optionally filtered by type. |
| `clear_signals` | `self, signal_type: str \| None = None` | `int` | Remove pending signals and return the count cleared. |

### AgentHeartbeat

Dataclass holding heartbeat data for a single agent.

| Field | Type | Default |
|-------|------|---------|
| `agent_id` | `str` | — |
| `status` | `str` | — |
| `progress` | `float` | — |
| `current_task` | `str` | — |
| `last_beat` | `datetime` | — |
| `metadata` | `dict[str, Any]` | `field(default_factory=dict)` |
| `display_name` | `str \| None` | `None` |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | `self` | `dict[str, Any]` | Serialize to a dictionary. |
| `from_dict` | `cls, data: dict[str, Any]` | `AgentHeartbeat` | Deserialize from a dictionary. |

### HeartbeatCoordinator

Coordinates agent heartbeats using Redis TTL keys.

#### Constructor

| Parameter | Type | Default |
|-----------|------|---------|
| `memory` | — | — |
| `enable_streaming` | `bool` | `False` |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `start_heartbeat` | `self, agent_id: str, metadata: dict[str, Any] \| None = None, display_name: str \| None = None` | `None` | Register and begin a heartbeat for the given agent. |
| `beat` | `self, status: str = 'running', progress: float = 0.0, current_task: str = ''` | `None` | Emit a single heartbeat pulse with current status and progress. |
| `stop_heartbeat` | `self, final_status: str = 'completed'` | `None` | Stop the heartbeat and record a final status. |
| `get_active_agents` | `self` | `list[AgentHeartbeat]` | Return heartbeat records for all currently active agents. |
| `is_agent_alive` | `self, agent_id: str` | `bool` | Return whether the given agent has a live heartbeat. |
| `get_agent_status` | `self, agent_id: str` | `AgentHeartbeat \| None` | Return the latest heartbeat record for the given agent. |
| `get_stale_agents` | `self, threshold_seconds: float = 60.0` | `list[AgentHeartbeat]` | Return agents whose last beat exceeds the staleness threshold. |

### ApprovalRequest

Dataclass representing a human approval request with workflow context.

| Field | Type | Default |
|-------|------|---------|
| `request_id` | `str` | — |
| `approval_type` | `str` | — |
| `agent_id` | `str` | — |
| `context` | `dict[str, Any]` | — |
| `timestamp` | `datetime` | — |
| `timeout_seconds` | `float` | — |
| `status` | `str` | `'pending'` |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | `self` | `dict[str, Any]` | Serialize to a dictionary. |
| `from_dict` | `cls, data: dict[str, Any]` | `ApprovalRequest` | Deserialize from a dictionary. |

### ApprovalResponse

Dataclass representing a human responder's decision on an approval request.

| Field | Type | Default |
|-------|------|---------|
| `request_id` | `str` | — |
| `approved` | `bool` | — |
| `responder` | `str` | — |
| `reason` | `str` | `''` |
| `timestamp` | `datetime` | `field(default_factory=lambda : datetime.now(timezone.utc))` |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | `self` | `dict[str, Any]` | Serialize to a dictionary. |
| `from_dict` | `cls, data: dict[str, Any]` | `ApprovalResponse` | Deserialize from a dictionary. |

### ApprovalGate

Human approval gates for workflow control.

#### Constructor

| Parameter | Type | Default |
|-----------|------|---------|
| `memory` | — | — |
| `agent_id` | `str \| None` | `None` |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `request_approval` | `self, approval_type: str, context: dict[str, Any] \| None = None, timeout: float \| None = None` | `ApprovalResponse` | Submit an approval request and wait for a human response. |
| `respond_to_approval` | `self, request_id: str, approved: bool, responder: str, reason: str = ''` | `bool` | Record a human decision for the given request. |
| `get_pending_approvals` | `self, approval_type: str \| None = None` | `list[ApprovalRequest]` | Return all pending approval requests, optionally filtered by type. |
| `clear_expired_requests` | `self` | `int` | Remove timed-out requests and return the count cleared. |

### StreamEvent

Dataclass representing an event published to a Redis Stream.

| Field | Type | Default |
|-------|------|---------|
| `event_id` | `str` | — |
| `event_type` | `str` | — |
| `timestamp` | `datetime` | — |
| `data` | `dict[str, Any]` | — |
| `source` | `str` | `'attune'` |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | `self` | `dict[str, Any]` | Serialize to a dictionary. |
| `from_redis_entry` | `cls, event_id: str, entry_data: dict[bytes, bytes]` | `StreamEvent` | Deserialize from a raw Redis Stream entry. |

### EventStreamer

Real-time event streaming using Redis Streams.

#### Constructor

| Parameter | Type | Default |
|-----------|------|---------|
| `memory` | — | — |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `publish_event` | `self, event_type: str, data: dict[str, Any], source: str = 'attune'` | `str` | Publish an event to the stream and return its event ID. |
| `consume_events` | `self, event_types: list[str] \| None = None, block_ms: int \| None = None, count: int = 10, start_id: str = '$'` | `Iterator[StreamEvent]` | Yield events from the stream, optionally blocking for new entries. |
| `get_recent_events` | `self, event_type: str, count: int = 100, start_id: str = '-', end_id: str = '+'` | `list[StreamEvent]` | Return recent events of the given type within the specified ID range. |
| `get_stream_info` | `self, event_type: str` | `dict[str, Any]` | Return metadata about the specified stream. |
| `delete_stream` | `self, event_type: str` | `bool` | Delete the entire stream for the given event type. |
| `trim_stream` | `self, event_type: str, max_length: int = 1000` | `int` | Trim the stream to `max_length` entries and return the count removed. |

## Functions

| Function | Parameters | Returns | Description | File |
|----------|------------|---------|-------------|------|
| `main` | — | `int` | Telemetry CLI entry point. | `src/attune/telemetry/__main__.py` |
| `cmd_sonnet_opus_analysis` | `args: Any` | `int` | Show Sonnet 4.5 -> Opus 4.5 fallback analysis and cost savings. | `src/attune/telemetry/cli_analysis.py` |
| `cmd_file_test_status` | `args: Any` | `int` | Show per-file test status. | `src/attune/telemetry/cli_analysis.py` |
| `cmd_tier1_status` | `args: Any` | `int` | Show comprehensive Tier 1 automation status. | `src/attune/telemetry/cli_automation.py` |
| `cmd_task_routing_report` | `args: Any` | `int` | Show detailed task routing report. | `src/attune/telemetry/cli_automation.py` |
| `cmd_test_status` | `args: Any` | `int` | Show test execution status. | `src/attune/telemetry/cli_automation.py` |
| `cmd_agent_performance` | `args: Any` | `int` | Show agent performance metrics. | `src/attune/telemetry/cli_automation.py` |
| `cmd_telemetry_show` | `args: Any` | `int` | Show recent telemetry entries. | `src/attune/telemetry/cli_core.py` |
| `cmd_telemetry_savings` | `args: Any` | `int` | Calculate and display cost savings. | `src/attune/telemetry/cli_core.py` |
| `cmd_telemetry_cache_stats` | `args: Any` | `int` | Show prompt caching performance statistics. | `src/attune/telemetry/cli_core.py` |
| `cmd_telemetry_compare` | `args: Any` | `int` | Compare telemetry across two time periods. | `src/attune/telemetry/cli_core.py` |
| `cmd_telemetry_reset` | `args: Any` | `int` | Reset/clear all telemetry data. | `src/attune/telemetry/cli_core.py` |
| `cmd_telemetry_export` | `args: Any` | `int` | Export
