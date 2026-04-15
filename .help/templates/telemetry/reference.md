---
type: reference
feature: telemetry
depth: reference
generated_at: 2026-04-14T15:19:53.996016+00:00
source_hash: 295e5e35ecdbf0e851c8b1779b79738f03b705495583edbf2e6416bf4fe17480
status: generated
---

# Telemetry reference

## Classes

### CoordinationSignal

Coordination signal between agents.

| Field | Type | Default |
|-------|------|---------|
| signal_id | str | |
| signal_type | str | |
| source_agent | str | |
| target_agent | str \| None | |
| payload | dict[str, Any] | |
| timestamp | datetime | |
| ttl_seconds | int | 60 |

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| to_dict | self | dict[str, Any] | Convert to dictionary |
| from_dict | cls, data: dict[str, Any] | CoordinationSignal | Create from dictionary |

### CoordinationSignals

TTL-based inter-agent coordination signals.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| __init__ | self, memory = None, agent_id: str \| None = None, enable_streaming: bool = False | | Initialize coordination signals |
| signal | self, signal_type: str, source_agent: str \| None = None, target_agent: str \| None = None, payload: dict[str, Any] \| None = None, ttl_seconds: int \| None = None, credentials: AgentCredentials \| None = None | str | Send signal to specific agent |
| broadcast | self, signal_type: str, source_agent: str \| None = None, payload: dict[str, Any] \| None = None, ttl_seconds: int \| None = None, credentials: AgentCredentials \| None = None | str | Broadcast signal to all agents |
| wait_for_signal | self, signal_type: str, source_agent: str \| None = None, timeout: float = 30.0, poll_interval: float = 0.5 | CoordinationSignal \| None | Wait for specific signal |
| check_signal | self, signal_type: str, source_agent: str \| None = None, consume: bool = True | CoordinationSignal \| None | Check for signal without waiting |
| get_pending_signals | self, signal_type: str \| None = None | list[CoordinationSignal] | Get all pending signals |
| clear_signals | self, signal_type: str \| None = None | int | Clear signals and return count |

### AgentHeartbeat

Agent heartbeat data structure.

| Field | Type | Default |
|-------|------|---------|
| agent_id | str | |
| status | str | |
| progress | float | |
| current_task | str | |
| last_beat | datetime | |
| metadata | dict[str, Any] | field(default_factory=dict) |
| display_name | str \| None | None |

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| to_dict | self | dict[str, Any] | Convert to dictionary |
| from_dict | cls, data: dict[str, Any] | AgentHeartbeat | Create from dictionary |

### HeartbeatCoordinator

Coordinates agent heartbeats using Redis TTL keys.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| __init__ | self, memory = None, enable_streaming: bool = False | | Initialize heartbeat coordinator |
| start_heartbeat | self, agent_id: str, metadata: dict[str, Any] \| None = None, display_name: str \| None = None | None | Start heartbeat for agent |
| beat | self, status: str = 'running', progress: float = 0.0, current_task: str = '' | None | Send heartbeat |
| stop_heartbeat | self, final_status: str = 'completed' | None | Stop heartbeat with final status |
| get_active_agents | self | list[AgentHeartbeat] | Get all active agents |
| is_agent_alive | self, agent_id: str | bool | Check if agent is alive |
| get_agent_status | self, agent_id: str | AgentHeartbeat \| None | Get agent status |
| get_stale_agents | self, threshold_seconds: float = 60.0 | list[AgentHeartbeat] | Get agents past threshold |

### ApprovalRequest

Approval request with context for human decision.

| Field | Type | Default |
|-------|------|---------|
| request_id | str | |
| approval_type | str | |
| agent_id | str | |
| context | dict[str, Any] | |
| timestamp | datetime | |
| timeout_seconds | float | |
| status | str | 'pending' |

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| to_dict | self | dict[str, Any] | Convert to dictionary |
| from_dict | cls, data: dict[str, Any] | ApprovalRequest | Create from dictionary |

### ApprovalResponse

Response to an approval request.

| Field | Type | Default |
|-------|------|---------|
| request_id | str | |
| approved | bool | |
| responder | str | |
| reason | str | '' |
| timestamp | datetime | field(default_factory=lambda : datetime.now(timezone.utc)) |

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| to_dict | self | dict[str, Any] | Convert to dictionary |
| from_dict | cls, data: dict[str, Any] | ApprovalResponse | Create from dictionary |

### ApprovalGate

Human approval gates for workflow control.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| __init__ | self, memory = None, agent_id: str \| None = None | | Initialize approval gate |
| request_approval | self, approval_type: str, context: dict[str, Any] \| None = None, timeout: float \| None = None | ApprovalResponse | Request human approval |
| respond_to_approval | self, request_id: str, approved: bool, responder: str, reason: str = '' | bool | Respond to approval request |
| get_pending_approvals | self, approval_type: str \| None = None | list[ApprovalRequest] | Get pending approval requests |
| clear_expired_requests | self | int | Clear expired requests and return count |

### StreamEvent

Event published to Redis Stream.

| Field | Type | Default |
|-------|------|---------|
| event_id | str | |
| event_type | str | |
| timestamp | datetime | |
| data | dict[str, Any] | |
| source | str | 'attune' |

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| to_dict | self | dict[str, Any] | Convert to dictionary |
| from_redis_entry | cls, event_id: str, entry_data: dict[bytes, bytes] | StreamEvent | Create from Redis entry |

### EventStreamer

Real-time event streaming using Redis Streams.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| __init__ | self, memory = None | | Initialize event streamer |
| publish_event | self, event_type: str, data: dict[str, Any], source: str = 'attune' | str | Publish event to stream |
| consume_events | self, event_types: list[str] \| None = None, block_ms: int \| None = None, count: int = 10, start_id: str = '$' | Iterator[StreamEvent] | Consume events from streams |
| get_recent_events | self, event_type: str, count: int = 100, start_id: str = '-', end_id: str = '+' | list[StreamEvent] | Get recent events |
| get_stream_info | self, event_type: str | dict[str, Any] | Get stream information |
| delete_stream | self, event_type: str | bool | Delete stream |
| trim_stream | self, event_type: str, max_length: int = 1000 | int | Trim stream to max length |

### FeatureStatus

Status of an optional feature.

## CLI Commands

| Command | Parameters | Returns | Description |
|---------|------------|---------|-------------|
| main | | int | Telemetry CLI entry point |
| cmd_sonnet_opus_analysis | args: Any | int | Show Sonnet 4.5 -> Opus 4.5 fallback analysis and cost savings |
| cmd_file_test_status | args: Any | int | Show per-file test status |
| cmd_tier1_status | args: Any | int | Show comprehensive Tier 1 automation status |
| cmd_task_routing_report | args: Any | int | Show detailed task routing report |
| cmd_test_status | args: Any | int | Show test execution status |
| cmd_agent_performance | args: Any | int | Show agent performance metrics |
| cmd_telemetry_show | args: Any | int | Show recent telemetry entries |
| cmd_telemetry_savings | args: Any | int | Calculate and display cost savings |
| cmd_telemetry_cache_stats | args: Any | int | Show prompt caching performance statistics |

All CLI commands return 0 on success.
