---
type: reference
feature: telemetry
depth: reference
generated_at: 2026-05-04T02:37:43.292955+00:00
source_hash: ed8485991002cc1c218f67b4f33f230bcbdc4325599a2e03f2bbe584d94a5e90
status: generated
---

# Telemetry reference

Track agent coordination, heartbeats, approval workflows, and streaming events across Attune AI systems. Provides Redis-backed coordination signals, TTL-based agent tracking, human approval gates, and privacy-first usage telemetry.

## Agent Coordination

### CoordinationSignal

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `signal_id` | `str` | - | Unique identifier for the signal |
| `signal_type` | `str` | - | Type classification for filtering |
| `source_agent` | `str` | - | ID of the sending agent |
| `target_agent` | `str \| None` | - | ID of the receiving agent (None for broadcast) |
| `payload` | `dict[str, Any]` | - | Signal data content |
| `timestamp` | `datetime` | - | When the signal was created |
| `ttl_seconds` | `int` | `60` | Time-to-live before automatic expiry |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict(self)` | `dict[str, Any]` | Serialize signal to dictionary |
| `from_dict(cls, data: dict[str, Any])` | `CoordinationSignal` | Deserialize signal from dictionary |

### CoordinationSignals

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__(self, memory, agent_id, enable_streaming)` | `memory=None, agent_id: str \| None = None, enable_streaming: bool = False` | - | Initialize coordination system |
| `signal(self, signal_type, source_agent, target_agent, payload, ttl_seconds, credentials)` | `signal_type: str, source_agent: str \| None = None, target_agent: str \| None = None, payload: dict[str, Any] \| None = None, ttl_seconds: int \| None = None, credentials: AgentCredentials \| None = None` | `str` | Send signal to specific agent |
| `broadcast(self, signal_type, source_agent, payload, ttl_seconds, credentials)` | `signal_type: str, source_agent: str \| None = None, payload: dict[str, Any] \| None = None, ttl_seconds: int \| None = None, credentials: AgentCredentials \| None = None` | `str` | Send signal to all agents |
| `wait_for_signal(self, signal_type, source_agent, timeout, poll_interval)` | `signal_type: str, source_agent: str \| None = None, timeout: float = 30.0, poll_interval: float = 0.5` | `CoordinationSignal \| None` | Block until signal arrives or timeout |
| `check_signal(self, signal_type, source_agent, consume)` | `signal_type: str, source_agent: str \| None = None, consume: bool = True` | `CoordinationSignal \| None` | Non-blocking signal check |
| `get_pending_signals(self, signal_type)` | `signal_type: str \| None = None` | `list[CoordinationSignal]` | Get all pending signals |
| `clear_signals(self, signal_type)` | `signal_type: str \| None = None` | `int` | Remove signals and return count cleared |

## Agent Tracking

### AgentHeartbeat

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent_id` | `str` | - | Unique agent identifier |
| `status` | `str` | - | Current agent status |
| `progress` | `float` | - | Task completion percentage |
| `current_task` | `str` | - | Description of current task |
| `last_beat` | `datetime` | - | Timestamp of last heartbeat |
| `metadata` | `dict[str, Any]` | `dict()` | Additional agent context |
| `display_name` | `str \| None` | `None` | Human-readable agent name |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict(self)` | `dict[str, Any]` | Serialize heartbeat to dictionary |
| `from_dict(cls, data: dict[str, Any])` | `AgentHeartbeat` | Deserialize heartbeat from dictionary |

### HeartbeatCoordinator

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__(self, memory, enable_streaming)` | `memory=None, enable_streaming: bool = False` | - | Initialize heartbeat coordinator |
| `start_heartbeat(self, agent_id, metadata, display_name)` | `agent_id: str, metadata: dict[str, Any] \| None = None, display_name: str \| None = None` | `None` | Begin heartbeat tracking |
| `beat(self, status, progress, current_task)` | `status: str = 'running', progress: float = 0.0, current_task: str = ''` | `None` | Send heartbeat update |
| `stop_heartbeat(self, final_status)` | `final_status: str = 'completed'` | `None` | Stop heartbeat tracking |
| `get_active_agents(self)` | - | `list[AgentHeartbeat]` | Get all active agents |
| `is_agent_alive(self, agent_id)` | `agent_id: str` | `bool` | Check if agent is sending heartbeats |
| `get_agent_status(self, agent_id)` | `agent_id: str` | `AgentHeartbeat \| None` | Get specific agent status |
| `get_stale_agents(self, threshold_seconds)` | `threshold_seconds: float = 60.0` | `list[AgentHeartbeat]` | Find agents exceeding stale threshold |

## Approval Gates

### ApprovalRequest

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `request_id` | `str` | - | Unique request identifier |
| `approval_type` | `str` | - | Type of approval needed |
| `agent_id` | `str` | - | ID of requesting agent |
| `context` | `dict[str, Any]` | - | Request context and details |
| `timestamp` | `datetime` | - | When request was created |
| `timeout_seconds` | `float` | - | Request expiry timeout |
| `status` | `str` | `'pending'` | Current request status |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict(self)` | `dict[str, Any]` | Serialize request to dictionary |
| `from_dict(cls, data: dict[str, Any])` | `ApprovalRequest` | Deserialize request from dictionary |

### ApprovalResponse

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `request_id` | `str` | - | ID of the approval request |
| `approved` | `bool` | - | Whether request was approved |
| `responder` | `str` | - | ID of the responding user |
| `reason` | `str` | `''` | Explanation for the decision |
| `timestamp` | `datetime` | `datetime.now(timezone.utc)` | When response was given |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict(self)` | `dict[str, Any]` | Serialize response to dictionary |
| `from_dict(cls, data: dict[str, Any])` | `ApprovalResponse` | Deserialize response from dictionary |

### ApprovalGate

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__(self, memory, agent_id)` | `memory=None, agent_id: str \| None = None` | - | Initialize approval gate |
| `request_approval(self, approval_type, context, timeout)` | `approval_type: str, context: dict[str, Any] \| None = None, timeout: float \| None = None` | `ApprovalResponse` | Request human approval and wait |
| `respond_to_approval(self, request_id, approved, responder, reason)` | `request_id: str, approved: bool, responder: str, reason: str = ''` | `bool` | Respond to pending approval request |
| `get_pending_approvals(self, approval_type)` | `approval_type: str \| None = None` | `list[ApprovalRequest]` | Get all pending approval requests |
| `clear_expired_requests(self)` | - | `int` | Remove expired requests and return count |

## Event Streaming

### StreamEvent

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `event_id` | `str` | - | Unique event identifier |
| `event_type` | `str` | - | Type classification for filtering |
| `timestamp` | `datetime` | - | When event occurred |
| `data` | `dict[str, Any]` | - | Event payload |
| `source` | `str` | `'attune'` | Source system that generated event |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict(self)` | `dict[str, Any]` | Serialize event to dictionary |
| `from_redis_entry(cls, event_id: str, entry_data: dict[bytes, bytes])` | `StreamEvent` | Deserialize event from Redis stream entry |

### EventStreamer

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__(self, memory)` | `memory=None` | - | Initialize event streamer |
| `publish_event(self, event_type, data, source)` | `event_type: str, data: dict[str, Any], source: str = 'attune'` | `str` | Publish event to stream |
| `consume_events(self, event_types, block_ms, count, start_id)` | `event_types: list[str] \| None = None, block_ms: int \| None = None, count: int = 10, start_id: str = '$'` | `Iterator[StreamEvent]` | Consume events from stream |
| `get_recent_events(self, event_type, count, start_id, end_id)` | `event_type: str, count: int = 100, start_id: str = '-', end_id: str = '+'` | `list[StreamEvent]` | Get recent events by type |
| `get_stream_info(self, event_type)` | `event_type: str` | `dict[str, Any]` | Get stream metadata and statistics |
| `delete_stream(self, event_type)` | `event_type: str` | `bool` | Delete entire stream |
| `trim_stream(self, event_type, max_length)` | `event_type: str, max_length: int = 1000` | `int` | Trim stream to maximum length |

## CLI Commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `main()` | - | `int` | Telemetry CLI entry point |
| `cmd_sonnet_opus_analysis(args)` | `args: Any` | `int` | Show Sonnet 4.5 -> Opus 4.5 fallback analysis and cost savings |
| `cmd_file_test_status(args)` | `args: Any` | `int` | Show per-file test status |
| `cmd_tier1_status(args)` | `args: Any` | `int` | Show comprehensive Tier 1 automation status |
| `cmd_task_routing_report(args)` | `args: Any` | `int` | Show detailed task routing report |
| `cmd_test_status(args)` | `args: Any` | `int` | Show test execution status |
| `cmd_agent_performance(args)` | `args: Any` | `int` | Show agent performance metrics |
| `cmd_telemetry_show(args)` | `args: Any` | `int` | Show recent telemetry entries |
| `cmd_telemetry_savings(args)` | `args: Any` | `int` | Calculate and display cost savings |
| `cmd_telemetry_cache_stats(args)` | `args: Any` | `int` | Show prompt caching performance statistics |

## Constants

| Constant | Type | Value | Description |
|----------|------|-------|-------------|
| `_LOG_VERSION` | `str` | `'1.0'` | Telemetry log format version |
| `_DEFAULT_FILE` | `str` | `'help_queries.jsonl'` | Default telemetry data filename |

## Source files

- `src/attune/telemetry/**`

## Tags

`telemetry`, `metrics`
