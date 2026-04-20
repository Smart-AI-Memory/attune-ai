---
type: reference
feature: telemetry
depth: reference
generated_at: 2026-04-20T01:23:24.449066+00:00
source_hash: 6acf95560dfe49824641ad827861534eaea26c9226d58caa5c047e5a5c955c0d
status: generated
---

# Telemetry reference

Track agent coordination, collect usage metrics, and enable human oversight for Attune AI workflows.

## Classes

| Class | Description |
|-------|-------------|
| `CoordinationSignal` | Coordination signal between agents |
| `CoordinationSignals` | TTL-based inter-agent coordination signals |
| `AgentHeartbeat` | Agent heartbeat data structure |
| `HeartbeatCoordinator` | Coordinates agent heartbeats using Redis TTL keys |
| `ApprovalRequest` | Approval request with context for human decision |
| `ApprovalResponse` | Response to an approval request |
| `ApprovalGate` | Human approval gates for workflow control |
| `StreamEvent` | Event published to Redis Stream |
| `EventStreamer` | Real-time event streaming using Redis Streams |
| `FeatureStatus` | Status of an optional feature |
| `FeatureInfo` | Information about a telemetry feature |
| `TelemetryFeatures` | Check availability of telemetry features |
| `FeedbackLoop` | Agent-to-LLM feedback loop for quality-based learning |
| `ModelTier` | Model tier enum matching workflows.base.ModelTier |
| `FeedbackEntry` | Quality feedback for an LLM response |
| `QualityStats` | Quality statistics for a workflow stage |
| `TierRecommendation` | Tier recommendation based on quality feedback |
| `HelpTracker` | Append-only JSONL tracker for help-system queries |
| `UsageTracker` | Privacy-first local telemetry tracker |

## CoordinationSignal

| Field | Type | Default |
|-------|------|---------|
| `signal_id` | `str` | - |
| `signal_type` | `str` | - |
| `source_agent` | `str` | - |
| `target_agent` | `str \| None` | - |
| `payload` | `dict[str, Any]` | - |
| `timestamp` | `datetime` | - |
| `ttl_seconds` | `int` | `60` |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict()` | `dict[str, Any]` | Convert signal to dictionary |
| `from_dict(data)` | `CoordinationSignal` | Create signal from dictionary |

## CoordinationSignals

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `memory=None, agent_id: str \| None = None, enable_streaming: bool = False` | - | Initialize coordination signals |
| `signal` | `signal_type: str, source_agent: str \| None = None, target_agent: str \| None = None, payload: dict[str, Any] \| None = None, ttl_seconds: int \| None = None, credentials: AgentCredentials \| None = None` | `str` | Send coordination signal |
| `broadcast` | `signal_type: str, source_agent: str \| None = None, payload: dict[str, Any] \| None = None, ttl_seconds: int \| None = None, credentials: AgentCredentials \| None = None` | `str` | Broadcast signal to all agents |
| `wait_for_signal` | `signal_type: str, source_agent: str \| None = None, timeout: float = 30.0, poll_interval: float = 0.5` | `CoordinationSignal \| None` | Wait for specific signal |
| `check_signal` | `signal_type: str, source_agent: str \| None = None, consume: bool = True` | `CoordinationSignal \| None` | Check for signal without waiting |
| `get_pending_signals` | `signal_type: str \| None = None` | `list[CoordinationSignal]` | Get all pending signals |
| `clear_signals` | `signal_type: str \| None = None` | `int` | Clear signals and return count |

## AgentHeartbeat

| Field | Type | Default |
|-------|------|---------|
| `agent_id` | `str` | - |
| `status` | `str` | - |
| `progress` | `float` | - |
| `current_task` | `str` | - |
| `last_beat` | `datetime` | - |
| `metadata` | `dict[str, Any]` | `field(default_factory=dict)` |
| `display_name` | `str \| None` | `None` |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict()` | `dict[str, Any]` | Convert heartbeat to dictionary |
| `from_dict(data)` | `AgentHeartbeat` | Create heartbeat from dictionary |

## HeartbeatCoordinator

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `memory=None, enable_streaming: bool = False` | - | Initialize heartbeat coordinator |
| `start_heartbeat` | `agent_id: str, metadata: dict[str, Any] \| None = None, display_name: str \| None = None` | `None` | Start heartbeat for agent |
| `beat` | `status: str = 'running', progress: float = 0.0, current_task: str = ''` | `None` | Send heartbeat update |
| `stop_heartbeat` | `final_status: str = 'completed'` | `None` | Stop heartbeat for agent |
| `get_active_agents` | - | `list[AgentHeartbeat]` | Get all active agents |
| `is_agent_alive` | `agent_id: str` | `bool` | Check if agent is alive |
| `get_agent_status` | `agent_id: str` | `AgentHeartbeat \| None` | Get agent status |
| `get_stale_agents` | `threshold_seconds: float = 60.0` | `list[AgentHeartbeat]` | Get agents that haven't sent heartbeats |

## ApprovalRequest

| Field | Type | Default |
|-------|------|---------|
| `request_id` | `str` | - |
| `approval_type` | `str` | - |
| `agent_id` | `str` | - |
| `context` | `dict[str, Any]` | - |
| `timestamp` | `datetime` | - |
| `timeout_seconds` | `float` | - |
| `status` | `str` | `'pending'` |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict()` | `dict[str, Any]` | Convert request to dictionary |
| `from_dict(data)` | `ApprovalRequest` | Create request from dictionary |

## ApprovalResponse

| Field | Type | Default |
|-------|------|---------|
| `request_id` | `str` | - |
| `approved` | `bool` | - |
| `responder` | `str` | - |
| `reason` | `str` | `''` |
| `timestamp` | `datetime` | `field(default_factory=lambda : datetime.now(timezone.utc))` |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict()` | `dict[str, Any]` | Convert response to dictionary |
| `from_dict(data)` | `ApprovalResponse` | Create response from dictionary |

## ApprovalGate

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `memory=None, agent_id: str \| None = None` | - | Initialize approval gate |
| `request_approval` | `approval_type: str, context: dict[str, Any] \| None = None, timeout: float \| None = None` | `ApprovalResponse` | Request human approval |
| `respond_to_approval` | `request_id: str, approved: bool, responder: str, reason: str = ''` | `bool` | Respond to approval request |
| `get_pending_approvals` | `approval_type: str \| None = None` | `list[ApprovalRequest]` | Get pending approval requests |
| `clear_expired_requests` | - | `int` | Clear expired requests and return count |

## StreamEvent

| Field | Type | Default |
|-------|------|---------|
| `event_id` | `str` | - |
| `event_type` | `str` | - |
| `timestamp` | `datetime` | - |
| `data` | `dict[str, Any]` | - |
| `source` | `str` | `'attune'` |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict()` | `dict[str, Any]` | Convert event to dictionary |
| `from_redis_entry(event_id, entry_data)` | `StreamEvent` | Create event from Redis entry |

## EventStreamer

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `memory=None` | - | Initialize event streamer |
| `publish_event` | `event_type: str, data: dict[str, Any], source: str = 'attune'` | `str` | Publish event to stream |
| `consume_events` | `event_types: list[str] \| None = None, block_ms: int \| None = None, count: int = 10, start_id: str = '$'` | `Iterator[StreamEvent]` | Consume events from stream |
| `get_recent_events` | `event_type: str, count: int = 100, start_id: str = '-', end_id: str = '+'` | `list[StreamEvent]` | Get recent events |
| `get_stream_info` | `event_type: str` | `dict[str, Any]` | Get stream information |
| `delete_stream` | `event_type: str` | `bool` | Delete stream |
| `trim_stream` | `event_type: str, max_length: int = 1000` | `int` | Trim stream to max length |

## CLI Commands

| Function | Returns | Description |
|----------|---------|-------------|
| `main()` | `int` | Telemetry CLI entry point |
| `cmd_sonnet_opus_analysis(args)` | `int` | Show Sonnet 4.5 → Opus 4.5 fallback analysis and cost savings |
| `cmd_file_test_status(args)` | `int` | Show per-file test status |
| `cmd_tier1_status(args)` | `int` | Show comprehensive Tier 1 automation status |
| `cmd_task_routing_report(args)` | `int` | Show detailed task routing report |
| `cmd_test_status(args)` | `int` | Show test execution status |
| `cmd_agent_performance(args)` | `int` | Show agent performance metrics |
| `cmd_telemetry_show(args)` | `int` | Show recent telemetry entries |
| `cmd_telemetry_savings(args)` | `int` | Calculate and display cost savings |
| `cmd_telemetry_cache_stats(args)` | `int` | Show prompt caching performance statistics |

## Functions

| Function | Returns | Description |
|----------|---------|-------------|
| `get_tracker()` | `HelpTracker` | Return a process-wide default HelpTracker |
