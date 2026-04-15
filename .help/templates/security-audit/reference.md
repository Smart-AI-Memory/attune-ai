---
type: reference
feature: security-audit
depth: reference
generated_at: 2026-04-14T14:38:09.949722+00:00
source_hash: 1ad7c6ac653fba529260181790342f2f2a067d4d45c694665a849d4622176019
status: generated
---

# Security Audit reference

## SecurityAuditWorkflow

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `**kwargs: Any` | `None` | Initialize security audit workflow |
| `execute` | `**kwargs: Any` | `WorkflowResult` | Execute the security audit with specialized subagents |

## AlertEngine

Alert engine with SQLite storage and notification delivery.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `db_path: str \| Path = '.attune/alerts.db'`, `telemetry_dir: str \| Path \| None = None` | `None` | Initialize alert engine with database path |
| `add_alert` | `alert_id: str`, `name: str`, `metric: AlertMetric \| str`, `threshold: float`, `channel: AlertChannel \| str`, `webhook_url: str \| None = None`, `email: str \| None = None`, `cooldown_seconds: int = 3600`, `severity: AlertSeverity \| str = AlertSeverity.WARNING` | `AlertConfig` | Add a new alert configuration |
| `list_alerts` | | `list[AlertConfig]` | List all configured alerts |
| `get_alert` | `alert_id: str` | `AlertConfig \| None` | Get alert configuration by ID |
| `delete_alert` | `alert_id: str` | `bool` | Delete an alert by ID |
| `enable_alert` | `alert_id: str` | `bool` | Enable an alert by ID |
| `disable_alert` | `alert_id: str` | `bool` | Disable an alert by ID |
| `get_metrics` | | `dict[str, float]` | Get current telemetry metrics |
| `check_and_trigger` | | `list[AlertEvent]` | Check metrics and trigger alerts if thresholds exceeded |
| `get_alert_history` | `alert_id: str \| None = None`, `limit: int = 100` | `list[dict[str, Any]]` | Get alert trigger history |

## MultiBackend

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `backends: list[TelemetryBackend] \| None = None` | `None` | Initialize composite backend |
| `from_config` | `storage_dir: str = '.attune'` | `MultiBackend` | Create backend from configuration |
| `add_backend` | `backend: TelemetryBackend` | `None` | Add a telemetry backend |
| `remove_backend` | `backend: TelemetryBackend` | `None` | Remove a telemetry backend |
| `log_call` | `record: LLMCallRecord` | `None` | Log LLM call to all backends |
| `log_workflow` | `record: WorkflowRunRecord` | `None` | Log workflow run to all backends |
| `get_active_backends` | | `list[str]` | Get list of active backend names |
| `get_failed_backends` | | `list[str]` | Get list of failed backend names |
| `reset_failures` | | `None` | Reset failure status for all backends |
| `flush` | | `None` | Flush all backends |

## OTELBackend

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `endpoint: str \| None = None`, `batch_size: int = 10`, `retry_count: int = 3` | `None` | Initialize OpenTelemetry backend |
| `is_available` | | `bool` | Check if OpenTelemetry is available |
| `log_call` | `record: LLMCallRecord` | `None` | Log LLM call to OTEL collector |
| `log_workflow` | `record: WorkflowRunRecord` | `None` | Log workflow run to OTEL collector |
| `flush` | | `None` | Flush pending telemetry data |

## TelemetryBackend

Protocol for telemetry storage backends.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `log_call` | `record: LLMCallRecord` | `None` | Log an LLM call record |
| `log_workflow` | `record: WorkflowRunRecord` | `None` | Log a workflow run record |

## AlertConfig Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `alert_id` | `str` | | Unique identifier for the alert |
| `name` | `str` | | Human-readable alert name |
| `metric` | `AlertMetric` | | Metric to monitor |
| `threshold` | `float` | | Threshold value for triggering alert |
| `channel` | `AlertChannel` | | Notification channel for delivery |
| `webhook_url` | `str \| None` | `None` | Webhook URL for notifications |
| `email` | `str \| None` | `None` | Email address for notifications |
| `enabled` | `bool` | `True` | Whether alert is active |
| `cooldown_seconds` | `int` | `3600` | Cooldown period between alerts |
| `severity` | `AlertSeverity` | `AlertSeverity.WARNING` | Alert severity level |
| `created_at` | `datetime \| None` | `None` | Alert creation timestamp |

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | | `dict[str, Any]` | Convert configuration to dictionary |
| `from_dict` | `data: dict[str, Any]` | `AlertConfig` | Create configuration from dictionary |

## AlertEvent Fields

| Field | Type | Description |
|-------|------|-------------|
| `alert_id` | `str` | ID of the triggered alert |
| `alert_name` | `str` | Name of the triggered alert |
| `metric` | `AlertMetric` | Metric that triggered the alert |
| `current_value` | `float` | Current value of the metric |
| `threshold` | `float` | Threshold that was exceeded |
| `severity` | `AlertSeverity` | Severity level of the alert |
| `triggered_at` | `datetime` | When the alert was triggered |
| `message` | `str` | Alert message content |

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | | `dict[str, Any]` | Convert event to dictionary |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `alerts` | | | Alert management commands for LLM telemetry monitoring |
| `init` | `non_interactive: bool`, `metric: str \| None`, `threshold: float \| None`, `channel: str \| None`, `webhook_url: str \| None`, `email: str \| None` | | Initialize an alert with interactive workflow or CLI flags |
| `list_cmd` | `as_json: bool` | | List all configured alerts |
| `delete` | `alert_id: str` | | Delete an alert by ID |
| `enable` | `alert_id: str` | | Enable an alert by ID |
| `disable` | `alert_id: str` | | Disable an alert by ID |
| `watch` | `interval: int`, `daemon: bool`, `once: bool` | | Watch telemetry and trigger alerts when thresholds are exceeded |
| `history` | `alert_id: str \| None`, `limit: int`, `as_json: bool` | | View alert trigger history |
| `metrics` | `as_json: bool` | | View current telemetry metrics |
| `get_alert_engine` | `db_path: str \| Path = '.attune/alerts.db'` | `AlertEngine` | Get an AlertEngine instance |

## Constants

| Constant | Value |
|----------|-------|
| `SUBAGENT_NAMES` | `{'vuln-scanner', 'secret-detector', 'auth-reviewer', 'remediation-planner'}` |
