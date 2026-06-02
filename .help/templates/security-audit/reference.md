---
type: reference
name: security-audit-reference
feature: security-audit
depth: reference
generated_at: 2026-06-02T10:56:02.685158+00:00
source_hash: b5ac92e21712579189bcbb6c5f4ee162ee999a19b070da3f645661ffa7e81668
status: generated
---

# Security Audit reference

Scan code for security vulnerabilities — eval/exec, path traversal, hardcoded secrets, and injection risks.

## Classes

| Class | Description |
|-------|-------------|
| `SecurityAuditWorkflow` | SDK-native security audit with four specialized subagents. |
| `AlertEngine` | Alert engine with SQLite storage and notification delivery. |
| `AlertConfig` | Configuration for a single alert. |
| `AlertEvent` | An alert event that was triggered. |
| `AlertChannel` | Notification channels for alerts. |
| `AlertMetric` | Metrics that can be monitored. |
| `AlertSeverity` | Alert severity levels. |
| `TelemetryBackend` | Protocol for telemetry storage backends. |
| `MultiBackend` | Composite backend for simultaneous logging to multiple backends. |
| `OTELBackend` | OpenTelemetry backend for exporting telemetry to OTEL collectors. |

### `SecurityAuditWorkflow`

Coordinates four specialized subagents — `vuln-scanner`, `secret-detector`, `auth-reviewer`, and `remediation-planner` — to produce a unified security audit report.

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `*, system_prompt_suffix: str = '', **kwargs: Any` | `None` | Initializes the workflow with an optional system prompt suffix. |
| `execute` | `**kwargs: Any` | `WorkflowResult` | Runs all four subagents and synthesizes findings into a single report. |

### `AlertEngine`

Manages alert storage in SQLite, evaluates thresholds against live telemetry, and dispatches notifications.

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `db_path: str \| Path = '.attune/alerts.db', telemetry_dir: str \| Path \| None = None` | `None` | Creates an engine backed by a SQLite database at `db_path`. |
| `add_alert` | `alert_id: str, name: str, metric: AlertMetric \| str, threshold: float, channel: AlertChannel \| str, webhook_url: str \| None = None, email: str \| None = None, cooldown_seconds: int = 3600, severity: AlertSeverity \| str = AlertSeverity.WARNING` | `AlertConfig` | Registers a new alert and returns its configuration. |
| `list_alerts` | — | `list[AlertConfig]` | Returns all configured alerts. |
| `get_alert` | `alert_id: str` | `AlertConfig \| None` | Returns the configuration for a single alert, or `None` if not found. |
| `delete_alert` | `alert_id: str` | `bool` | Deletes an alert by ID. Returns `True` on success. |
| `enable_alert` | `alert_id: str` | `bool` | Enables an alert by ID. Returns `True` on success. |
| `disable_alert` | `alert_id: str` | `bool` | Disables an alert by ID. Returns `True` on success. |
| `get_metrics` | — | `dict[str, float]` | Returns current telemetry metric values keyed by metric name. |
| `check_and_trigger` | — | `list[AlertEvent]` | Evaluates all enabled alerts and fires notifications for any that exceed their thresholds. |
| `get_alert_history` | `alert_id: str \| None = None, limit: int = 100` | `list[dict[str, Any]]` | Returns past trigger records, optionally filtered to one alert. |

### `AlertConfig`

**[dataclass]** Configuration for a single alert.

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
| `to_dict` | — | `dict[str, Any]` | Serializes the configuration to a plain dictionary. |
| `from_dict` | `data: dict[str, Any]` | `AlertConfig` | Deserializes an `AlertConfig` from a plain dictionary. |

### `AlertEvent`

**[dataclass]** A triggered alert event, capturing the metric value and context at the moment of firing.

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
| `to_dict` | — | `dict[str, Any]` | Serializes the event to a plain dictionary. |

### `MultiBackend`

Routes telemetry records to multiple storage backends simultaneously, tracking failures per backend.

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `backends: list[TelemetryBackend] \| None = None` | `None` | Creates a composite backend from an optional initial list. |
| `from_config` | `storage_dir: str = '.attune'` | `MultiBackend` | Creates a `MultiBackend` from the configuration at `storage_dir`. |
| `add_backend` | `backend: TelemetryBackend` | `None` | Adds a backend to the active set. |
| `remove_backend` | `backend: TelemetryBackend` | `None` | Removes a backend from the active set. |
| `log_call` | `record: LLMCallRecord` | `None` | Writes an LLM call record to all active backends. |
| `log_workflow` | `record: WorkflowRunRecord` | `None` | Writes a workflow run record to all active backends. |
| `get_active_backends` | — | `list[str]` | Returns the names of currently active backends. |
| `get_failed_backends` | — | `list[str]` | Returns the names of backends that have encountered errors. |
| `reset_failures` | — | `None` | Clears the failure state for all backends. |
| `flush` | — | `None` | Flushes all pending records in active backends. |

### `OTELBackend`

Exports telemetry records to an OpenTelemetry collector, with configurable batching and retry.

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `endpoint: str \| None = None, batch_size: int = 10, retry_count: int = 3` | `None` | Connects to an OTEL collector endpoint with the given batch and retry settings. |
| `is_available` | — | `bool` | Returns `True` if the OTEL endpoint is reachable. |
| `log_call` | `record: LLMCallRecord` | `None` | Buffers an LLM call record for export. |
| `log_workflow` | `record: WorkflowRunRecord` | `None` | Buffers a workflow run record for export. |
| `flush` | — | `None` | Exports all buffered records to the OTEL collector. |

### `TelemetryBackend`

Protocol for telemetry storage backends.

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `log_call` | `record: LLMCallRecord` | `None` | Writes an LLM call record to the backend. |
| `log_workflow` | `record: WorkflowRunRecord` | `None` | Writes a workflow run record to the backend. |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_alert_engine` | `db_path: str \| Path = '.attune/alerts.db'` | `AlertEngine` | Returns an `AlertEngine` instance backed by the given SQLite database. |
| `collect_metrics` | `telemetry_dir: Path` | `dict[str, float]` | Collects current telemetry metrics from JSONL files in `telemetry_dir`. |
| `get_multi_backend` | `storage_dir: str = '.attune'` | `MultiBackend` | Returns or creates the global `MultiBackend` instance. |
| `reset_multi_backend` | — | `None` | Resets the global `MultiBackend` instance. |
| `deliver_notification` | `alert: AlertConfig, event: AlertEvent` | `bool` | Dispatches a notification through the channel configured on `alert`. |
| `deliver_webhook` | `alert: AlertConfig, event: AlertEvent` | `bool` | Delivers an alert notification via webhook (Slack, Discord, etc.). |
| `deliver_email` | `alert: AlertConfig, event: AlertEvent` | `bool` | Delivers an alert notification via email. |
| `deliver_stdout` | `event: AlertEvent` | `bool` | Delivers an alert notification to stdout. |
| `alerts` | — | — | Alert management commands for LLM telemetry monitoring. |
| `init` | `non_interactive: bool, metric: str \| None, threshold: float \| None, channel: str \| None, webhook_url: str \| None, email: str \| None` | — | Initializes an alert interactively or from CLI flags. |
| `list_cmd` | `as_json: bool` | — | Lists all configured alerts. |
| `delete` | `alert_id: str` | — | Deletes an alert by ID. |
| `enable` | `alert_id: str` | — | Enables an alert by ID. |
| `disable` | `alert_id: str` | — | Disables an alert by ID. |
| `watch` | `interval: int, daemon: bool, once: bool` | — | Polls telemetry and fires alerts when thresholds are exceeded. |
| `history` | `alert_id: str \| None, limit: int, as_json: bool` | — | Displays past alert trigger records. |
| `metrics` | `as_json: bool` | — | Displays current telemetry metric values. |

## Constants

### `_SUBAGENT_NAMES`

The four subagent roles coordinated by `SecurityAuditWorkflow`.

| Constant | Members |
|----------|---------|
| `_SUBAGENT_NAMES` | `'vuln-scanner'`, `'secret-detector'`, `'auth-reviewer'`, `'remediation-planner'` |

## Source files

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`
- `src/attune/monitoring/**`

## Tags

`security`, `audit`, `owasp`, `scanning`, `cve`
