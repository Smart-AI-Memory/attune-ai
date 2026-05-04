---
type: reference
feature: security-audit
depth: reference
generated_at: 2026-05-04T02:23:46.063870+00:00
source_hash: e5fdcf8a70287f5c6e2e0987e337f663cf89f93c523e4652f0c8a45e6709471e
status: generated
---

# Security Audit reference

Scan code for security vulnerabilities and monitor telemetry with alert thresholds.

## Classes

| Class | Description |
|-------|-------------|
| `SecurityAuditWorkflow` | SDK-native security audit with four specialized subagents |

### SecurityAuditWorkflow

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `**kwargs: Any` | `None` | Initialize the security audit workflow |
| `execute` | `**kwargs: Any` | `WorkflowResult` | Run the security audit on the specified path |

### Alert Management

| Class | Description |
|-------|-------------|
| `AlertEngine` | Alert engine with SQLite storage and notification delivery |
| `AlertConfig` | Configuration for a single alert |
| `AlertEvent` | An alert event that was triggered |

#### AlertEngine

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `db_path: str \| Path = '.attune/alerts.db', telemetry_dir: str \| Path \| None = None` | `None` | Initialize alert engine with database path |
| `add_alert` | `alert_id: str, name: str, metric: AlertMetric \| str, threshold: float, channel: AlertChannel \| str, webhook_url: str \| None = None, email: str \| None = None, cooldown_seconds: int = 3600, severity: AlertSeverity \| str = AlertSeverity.WARNING` | `AlertConfig` | Add a new alert configuration |
| `list_alerts` | | `list[AlertConfig]` | List all configured alerts |
| `get_alert` | `alert_id: str` | `AlertConfig \| None` | Get alert configuration by ID |
| `delete_alert` | `alert_id: str` | `bool` | Delete an alert by ID |
| `enable_alert` | `alert_id: str` | `bool` | Enable an alert by ID |
| `disable_alert` | `alert_id: str` | `bool` | Disable an alert by ID |
| `get_metrics` | | `dict[str, float]` | Get current telemetry metrics |
| `check_and_trigger` | | `list[AlertEvent]` | Check thresholds and trigger alerts |
| `get_alert_history` | `alert_id: str \| None = None, limit: int = 100` | `list[dict[str, Any]]` | View alert trigger history |

#### AlertConfig Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `alert_id` | `str` | | Unique identifier for the alert |
| `name` | `str` | | Human-readable alert name |
| `metric` | `AlertMetric` | | Metric to monitor |
| `threshold` | `float` | | Threshold value for triggering |
| `channel` | `AlertChannel` | | Notification channel |
| `webhook_url` | `str \| None` | `None` | Webhook URL for notifications |
| `email` | `str \| None` | `None` | Email address for notifications |
| `enabled` | `bool` | `True` | Whether the alert is active |
| `cooldown_seconds` | `int` | `3600` | Minimum time between notifications |
| `severity` | `AlertSeverity` | `AlertSeverity.WARNING` | Alert severity level |
| `created_at` | `datetime \| None` | `None` | When the alert was created |

#### AlertEvent Fields

| Field | Type | Description |
|-------|------|-------------|
| `alert_id` | `str` | ID of the triggered alert |
| `alert_name` | `str` | Name of the triggered alert |
| `metric` | `AlertMetric` | Metric that exceeded threshold |
| `current_value` | `float` | Current value of the metric |
| `threshold` | `float` | Configured threshold value |
| `severity` | `AlertSeverity` | Severity of the alert |
| `triggered_at` | `datetime` | When the alert was triggered |
| `message` | `str` | Alert message |

### Enums

| Enum | Description |
|------|-------------|
| `AlertChannel` | Notification channels for alerts |
| `AlertMetric` | Metrics that can be monitored |
| `AlertSeverity` | Alert severity levels |

### Telemetry Backends

| Class | Description |
|-------|-------------|
| `TelemetryBackend` | Protocol for telemetry storage backends |
| `MultiBackend` | Composite backend for simultaneous logging to multiple backends |
| `OTELBackend` | OpenTelemetry backend for exporting telemetry to OTEL collectors |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `alerts` | | | Alert management commands for LLM telemetry monitoring |
| `init` | `non_interactive: bool, metric: str \| None, threshold: float \| None, channel: str \| None, webhook_url: str \| None, email: str \| None` | | Initialize an alert with interactive workflow or CLI flags |
| `list_cmd` | `as_json: bool` | | List all configured alerts |
| `delete` | `alert_id: str` | | Delete an alert by ID |
| `enable` | `alert_id: str` | | Enable an alert by ID |
| `disable` | `alert_id: str` | | Disable an alert by ID |
| `watch` | `interval: int, daemon: bool, once: bool` | | Watch telemetry and trigger alerts when thresholds are exceeded |
| `history` | `alert_id: str \| None, limit: int, as_json: bool` | | View alert trigger history |
| `metrics` | `as_json: bool` | | View current telemetry metrics |
| `get_alert_engine` | `db_path: str \| Path = '.attune/alerts.db'` | `AlertEngine` | Get an AlertEngine instance |

## Constants

| Constant | Values | Description |
|----------|---------|-------------|
| `_SUBAGENT_NAMES` | `vuln-scanner`, `secret-detector`, `auth-reviewer`, `remediation-planner` | Names of specialized security audit subagents |
