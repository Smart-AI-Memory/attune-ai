---
type: reference
feature: security-audit
depth: reference
generated_at: 2026-04-19T18:43:10.556897+00:00
source_hash: 7561d25b90360cf091a4fb9961180c96361f86e49fed5a0d40830d980900d622
status: generated
---

# Security Audit reference

Scan code for security vulnerabilities and monitor telemetry with alerts.

## SecurityAuditWorkflow

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `**kwargs: Any` | `None` | Initialize the security audit workflow |
| `execute` | `**kwargs: Any` | `WorkflowResult` | Execute security audit with four specialized subagents |

## Alert Management

### AlertEngine

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `db_path: str \| Path = '.attune/alerts.db'`, `telemetry_dir: str \| Path \| None = None` | `None` | Initialize alert engine with SQLite storage |
| `add_alert` | `alert_id: str`, `name: str`, `metric: AlertMetric \| str`, `threshold: float`, `channel: AlertChannel \| str`, `webhook_url: str \| None = None`, `email: str \| None = None`, `cooldown_seconds: int = 3600`, `severity: AlertSeverity \| str = AlertSeverity.WARNING` | `AlertConfig` | Add a new alert configuration |
| `list_alerts` | | `list[AlertConfig]` | List all configured alerts |
| `get_alert` | `alert_id: str` | `AlertConfig \| None` | Get alert configuration by ID |
| `delete_alert` | `alert_id: str` | `bool` | Delete an alert by ID |
| `enable_alert` | `alert_id: str` | `bool` | Enable an alert by ID |
| `disable_alert` | `alert_id: str` | `bool` | Disable an alert by ID |
| `get_metrics` | | `dict[str, float]` | Get current telemetry metrics |
| `check_and_trigger` | | `list[AlertEvent]` | Check metrics and trigger alerts when thresholds are exceeded |
| `get_alert_history` | `alert_id: str \| None = None`, `limit: int = 100` | `list[dict[str, Any]]` | Get alert trigger history |

### Alert CLI Commands

| Function | Parameters | Description |
|----------|------------|-------------|
| `alerts` | | Alert management commands for LLM telemetry monitoring |
| `init` | `non_interactive: bool`, `metric: str \| None`, `threshold: float \| None`, `channel: str \| None`, `webhook_url: str \| None`, `email: str \| None` | Initialize an alert with interactive workflow or CLI flags |
| `list_cmd` | `as_json: bool` | List all configured alerts |
| `delete` | `alert_id: str` | Delete an alert by ID |
| `enable` | `alert_id: str` | Enable an alert by ID |
| `disable` | `alert_id: str` | Disable an alert by ID |
| `watch` | `interval: int`, `daemon: bool`, `once: bool` | Watch telemetry and trigger alerts when thresholds are exceeded |
| `history` | `alert_id: str \| None`, `limit: int`, `as_json: bool` | View alert trigger history |
| `metrics` | `as_json: bool` | View current telemetry metrics |
| `get_alert_engine` | `db_path: str \| Path = '.attune/alerts.db'` | Get an AlertEngine instance |

## Data Models

### AlertConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `alert_id` | `str` | | Unique identifier for the alert |
| `name` | `str` | | Human-readable alert name |
| `metric` | `AlertMetric` | | Metric to monitor |
| `threshold` | `float` | | Threshold value that triggers the alert |
| `channel` | `AlertChannel` | | Notification channel for delivery |
| `webhook_url` | `str \| None` | `None` | Webhook URL for notifications |
| `email` | `str \| None` | `None` | Email address for notifications |
| `enabled` | `bool` | `True` | Whether the alert is active |
| `cooldown_seconds` | `int` | `3600` | Minimum time between alert triggers |
| `severity` | `AlertSeverity` | `AlertSeverity.WARNING` | Alert severity level |
| `created_at` | `datetime \| None` | `None` | When the alert was created |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict` | `dict[str, Any]` | Convert alert config to dictionary |
| `from_dict` | `AlertConfig` | Create alert config from dictionary |

### AlertEvent

| Field | Type | Description |
|-------|------|-------------|
| `alert_id` | `str` | ID of the triggered alert |
| `alert_name` | `str` | Name of the triggered alert |
| `metric` | `AlertMetric` | Metric that triggered the alert |
| `current_value` | `float` | Current value of the metric |
| `threshold` | `float` | Threshold that was exceeded |
| `severity` | `AlertSeverity` | Severity level of the alert |
| `triggered_at` | `datetime` | When the alert was triggered |
| `message` | `str` | Alert message text |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict` | `dict[str, Any]` | Convert alert event to dictionary |

## Telemetry Backends

### MultiBackend

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `backends: list[TelemetryBackend] \| None = None` | `None` | Initialize composite backend |
| `from_config` | `storage_dir: str = '.attune'` | `MultiBackend` | Create backend from configuration |
| `add_backend` | `backend: TelemetryBackend` | `None` | Add a telemetry backend |
| `remove_backend` | `backend: TelemetryBackend` | `None` | Remove a telemetry backend |
| `log_call` | `record: LLMCallRecord` | `None` | Log an LLM call record |
| `log_workflow` | `record: WorkflowRunRecord` | `None` | Log a workflow run record |
| `get_active_backends` | | `list[str]` | Get list of active backend names |
| `get_failed_backends` | | `list[str]` | Get list of failed backend names |
| `reset_failures` | | `None` | Reset failure tracking for all backends |
| `flush` | | `None` | Flush all backends |

### OTELBackend

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `endpoint: str \| None = None`, `batch_size: int = 10`, `retry_count: int = 3` | `None` | Initialize OpenTelemetry backend |
| `is_available` | | `bool` | Check if OpenTelemetry dependencies are available |
| `log_call` | `record: LLMCallRecord` | `None` | Log an LLM call to OTEL |
| `log_workflow` | `record: WorkflowRunRecord` | `None` | Log a workflow run to OTEL |
| `flush` | | `None` | Flush pending telemetry data |

### TelemetryBackend

Protocol for telemetry storage backends.

| Method | Parameters | Description |
|--------|------------|-------------|
| `log_call` | `record: LLMCallRecord` | Log an LLM call record |
| `log_workflow` | `record: WorkflowRunRecord` | Log a workflow run record |

## Enums

### AlertChannel

Notification channels for alerts.

### AlertMetric

Metrics that can be monitored.

### AlertSeverity

Alert severity levels.

## Constants

### Subagent Configuration

| Constant | Values |
|----------|--------|
| `_SUBAGENT_NAMES` | `{'vuln-scanner', 'secret-detector', 'auth-reviewer', 'remediation-planner'}` |
