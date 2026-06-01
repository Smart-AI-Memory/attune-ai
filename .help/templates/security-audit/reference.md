---
feature: security-audit
depth: reference
generated_at: 2026-06-01T11:47:06.400451+00:00
source_hash: 6e7b17414ac506196ba40231988637e7d6eb64f9b1a8266dc41deaab14bee626
status: generated
---

# Security Audit reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `SecurityAuditWorkflow` | SDK-native security audit with four specialized subagents. | `src/attune/workflows/security_audit.py` |
| `AlertEngine` | Alert engine with SQLite storage and notification delivery. | `src/attune/monitoring/engine.py` |
| `AlertChannel` | Notification channels for alerts. | `src/attune/monitoring/models.py` |
| `AlertMetric` | Metrics that can be monitored. | `src/attune/monitoring/models.py` |
| `AlertSeverity` | Alert severity levels. | `src/attune/monitoring/models.py` |
| `AlertConfig` | Configuration for a single alert. | `src/attune/monitoring/models.py` |
| `AlertEvent` | An alert event that was triggered. | `src/attune/monitoring/models.py` |
| `TelemetryBackend` | Protocol for telemetry storage backends. | `src/attune/monitoring/multi_backend.py` |
| `MultiBackend` | Composite backend for simultaneous logging to multiple backends. | `src/attune/monitoring/multi_backend.py` |
| `OTELBackend` | OpenTelemetry backend for exporting telemetry to OTEL collectors. | `src/attune/monitoring/otel_backend.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `alerts()` | Alert management commands for LLM telemetry monitoring. | `src/attune/monitoring/alerts_cli.py` |
| `init()` | Initialize an alert with interactive workflow or CLI flags. | `src/attune/monitoring/alerts_cli.py` |
| `list_cmd()` | List all configured alerts. | `src/attune/monitoring/alerts_cli.py` |
| `delete()` | Delete an alert by ID. | `src/attune/monitoring/alerts_cli.py` |
| `enable()` | Enable an alert by ID. | `src/attune/monitoring/alerts_cli.py` |
| `disable()` | Disable an alert by ID. | `src/attune/monitoring/alerts_cli.py` |
| `watch()` | Watch telemetry and trigger alerts when thresholds are exceeded. | `src/attune/monitoring/alerts_cli.py` |
| `history()` | View alert trigger history. | `src/attune/monitoring/alerts_cli.py` |
| `metrics()` | View current telemetry metrics. | `src/attune/monitoring/alerts_cli.py` |
| `get_alert_engine()` | Get an AlertEngine instance. | `src/attune/monitoring/engine.py` |
| `collect_metrics()` | Collect current telemetry metrics from JSONL files. | `src/attune/monitoring/metrics.py` |
| `get_multi_backend()` | Get or create the global multi-backend instance. | `src/attune/monitoring/multi_backend.py` |
| `reset_multi_backend()` | Reset the global multi-backend instance. | `src/attune/monitoring/multi_backend.py` |
| `deliver_notification()` | Deliver notification through configured channel. | `src/attune/monitoring/notifications.py` |
| `deliver_webhook()` | Deliver alert via webhook (Slack, Discord, etc.). | `src/attune/monitoring/notifications.py` |
| `deliver_email()` | Deliver alert via email. | `src/attune/monitoring/notifications.py` |
| `deliver_stdout()` | Deliver alert to stdout/console. | `src/attune/monitoring/notifications.py` |


## Source files

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`
- `src/attune/monitoring/**`

## Tags

`security`, `audit`, `owasp`, `scanning`, `cve`
