---
type: reference
name: security-audit-reference
feature: security-audit
depth: reference
generated_at: 2026-05-16T06:19:45.797421+00:00
source_hash: b5ac92e21712579189bcbb6c5f4ee162ee999a19b070da3f645661ffa7e81668
status: generated
---

# Security Audit reference

Scan code for security vulnerabilities — eval/exec, path traversal, hardcoded secrets, and injection risks.

## Classes

The following classes implement the security audit workflow, alert management, and telemetry backends.

| Class | Description |
|-------|-------------|
| `SecurityAuditWorkflow` | SDK-native security audit with four specialized subagents. |
| `AlertEngine` | Alert engine with SQLite storage and notification delivery. |
| `AlertChannel` | Notification channels for alerts. |
| `AlertMetric` | Metrics that can be monitored. |
| `AlertSeverity` | Alert severity levels. |
| `AlertConfig` | Configuration for a single alert. |
| `AlertEvent` | An alert event that was triggered. |
| `TelemetryBackend` | Protocol for telemetry storage backends. |
| `MultiBackend` | Composite backend for simultaneous logging to multiple backends. |
| `OTELBackend` | OpenTelemetry backend for exporting telemetry to OTEL collectors. |

### `SecurityAuditWorkflow`

Coordinates four specialized subagents (`vuln-scanner`, `secret-detector`, `auth-reviewer`, `remediation-planner`) and synthesizes their findings into a single structured report.

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `*, system_prompt_suffix: str = '', **kwargs: Any` | `None` | Initialize the workflow. |
| `execute` | `**kwargs: Any` | `WorkflowResult` | Run the audit and return a unified report. |

### `AlertEngine`

#### Constructor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `db_path` | `str \| Path` | `'.attune/alerts.db'` | Path to the SQLite database file. |
| `telemetry_dir` | `str \| Path \| None` | `None` | Directory containing telemetry data. |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `add_alert` | `alert_id: str, name: str, metric: AlertMetric \| str, threshold: float, channel: AlertChannel \| str, webhook_url: str \| None = None, email: str \| None = None, cooldown_seconds: int = 3600, severity: AlertSeverity \| str = AlertSeverity.WARNING` | `AlertConfig` | Create and store a new alert configuration. |
| `list_alerts` | — | `list[AlertConfig]` | Return all configured alerts. |
| `get_alert` | `alert_id: str` | `AlertConfig \| None` | Retrieve a single alert by ID. |
| `delete_alert` | `alert_id: str` | `bool` | Delete an alert by ID. |
| `enable_alert` | `alert_id: str` | `bool` | Enable an alert by ID. |
| `disable_alert` | `alert_id: str` | `bool` | Disable an alert by ID. |
| `get_metrics` | — | `dict[str, float]` | Return current telemetry metric values. |
| `check_and_trigger` | — | `list[AlertEvent]` | Evaluate all alerts and trigger any that exceed their thresholds. |
| `get_alert_history` | `alert_id: str \| None = None, limit: int = 100` | `list[dict[str, Any]]` | Return past alert trigger events. |

### `AlertConfig` [dataclass]

Configuration for a single alert.

#### Fields

| Field | Type | Default |
|-------|------|---------|
| `alert_id` | `str` | — |
| `name` | `str` | — |
| `metric` | `AlertMetric` | — |
| `threshold` | `float` | — |
| `channel` | `AlertChannel` | — |
| `webhook_url` | `str \| None` | `None` |
| `email` | `str \| None` | `None` |
| `enabled` | `bool` | `True` |
| `cooldown_seconds` | `int` | `3600` |
| `severity` | `AlertSeverity` | `AlertSeverity.WARNING` |
| `created_at` | `datetime \| None` | `None` |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | — | `dict[str, Any]` | Serialize the alert configuration to a dictionary. |
| `from_dict` | `data: dict[str, Any]` | `AlertConfig` | Deserialize an alert configuration from a dictionary. |

### `AlertEvent` [dataclass]

An alert event that was triggered.

#### Fields

| Field | Type | Default |
|-------|------|---------|
| `alert_id` | `str` | — |
| `alert_name` | `str` | — |
| `metric` | `AlertMetric` | — |
| `current_value` | `float` | — |
| `threshold` | `float` | — |
| `severity` | `AlertSeverity` | — |
| `triggered_at` | `datetime` | — |
| `message` | `str` | — |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | — | `dict[str, Any]` | Serialize the event to a dictionary. |

### `MultiBackend`

#### Constructor

| Parameter | Type | Default |
|-----------|------|---------|
| `backends` | `list[TelemetryBackend] \| None` | `None` |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `from_config` | `storage_dir: str = '.attune'` | `MultiBackend` | Create a `MultiBackend` from a storage directory. |
| `add_backend` | `backend: TelemetryBackend` | `None` | Add a backend to the composite. |
| `remove_backend` | `backend: TelemetryBackend` | `None` | Remove a backend from the composite. |
| `log_call` | `record: LLMCallRecord` | `None` | Forward an LLM call record to all active backends. |
| `log_workflow` | `record: WorkflowRunRecord` | `None` | Forward a workflow run record to all active backends. |
| `get_active_backends` | — | `list[str]` | Return names of currently active backends. |
| `get_failed_backends` | — | `list[str]` | Return names of backends that have failed. |
| `reset_failures` | — | `None` | Clear failure state for all backends. |
| `flush` | — | `None` | Flush buffered records in all backends. |

### `OTELBackend`

#### Constructor

| Parameter | Type | Default |
|-----------|------|---------|
| `endpoint` | `str \| None` | `None` |
| `batch_size` | `int` | `10` |
| `retry_count` | `int` | `3` |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `is_available` | — | `bool` | Check whether the OTEL collector endpoint is reachable. |
| `log_call` | `record: LLMCallRecord` | `None` | Export an LLM call record to the OTEL collector. |
| `log_workflow` | `record: WorkflowRunRecord` | `None` | Export a workflow run record to the OTEL collector. |
| `flush` | — | `None` | Flush any buffered records to the OTEL collector. |

---

## Functions

### Workflow and engine

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_alert_engine` | `db_path: str \| Path = '.attune/alerts.db'` | `AlertEngine` | Get an `AlertEngine` instance. |
| `get_multi_backend` | `storage_dir: str = '.attune'` | `MultiBackend` | Get or create the global multi-backend instance. |
| `reset_multi_backend` | — | `None` | Reset the global multi-backend instance. |

### Metrics collection

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `collect_metrics` | `telemetry_dir: Path` | `dict[str, float]` | Collect current telemetry metrics from JSONL files. |

### Notification delivery

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `deliver_notification` | `alert: AlertConfig, event: AlertEvent` | `bool` | Deliver a notification through the channel configured on the alert. |
| `deliver_webhook` | `alert: AlertConfig, event: AlertEvent` | `bool` | Deliver an alert via webhook (Slack, Discord, etc.). |
| `deliver_email` | `alert: AlertConfig, event: AlertEvent` | `bool` | Deliver an alert via email. |
| `deliver_stdout` | `event: AlertEvent` | `bool` | Deliver an alert to stdout/console. |

### Alert CLI commands

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `alerts` | — | — | Alert management commands for LLM telemetry monitoring. |
| `init` | `non_interactive: bool, metric: str \| None, threshold: float \| None, channel: str \| None, webhook_url: str \| None, email: str \| None` | — | Initialize an alert with an interactive workflow or CLI flags. |
| `list_cmd` | `as_json: bool` | — | List all configured alerts. |
| `delete` | `alert_id: str` | — | Delete an alert by ID. |
| `enable` | `alert_id: str` | — | Enable an alert by ID. |
| `disable` | `alert_id: str` | — | Disable an alert by ID. |
| `watch` | `interval: int, daemon: bool, once: bool` | — | Watch telemetry and trigger alerts when thresholds are exceeded. |
| `history` | `alert_id: str \| None, limit: int, as_json: bool` | — | View alert trigger history. |
| `metrics` | `as_json: bool` | — | View current telemetry metrics. |

---

## Constants

### Subagents (`_SUBAGENT_NAMES`)

The four subagents that `SecurityAuditWorkflow` coordinates:

| Name |
|------|
| `vuln-scanner` |
| `secret-detector` |
| `auth-reviewer` |
| `remediation-planner` |

---

## Source files

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`
- `src/attune/monitoring/**`

## Tags

`security`, `audit`, `owasp`, `scanning`, `cve`
