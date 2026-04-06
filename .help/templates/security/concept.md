---
feature: security
depth: concept
generated_at: 2026-04-06T02:43:20.655653+00:00
source_hash: cbec6dd3b97445fab938304744407004a55adcad528e799ba56896c354f5ad8e
status: generated
---

# Security

## What

LLM telemetry monitoring with configurable alerts and path validation utilities for Attune AI

## When to use

Use security when you need to:

- Monitor LLM telemetry metrics and receive alerts when thresholds are exceeded
- Validate file and directory paths for security compliance
- Set up notification channels for alert delivery
- Track alert history and view current telemetry metrics

## Key components

| Component | Purpose |
|-----------|---------|
| `AlertEngine` | Manages alert storage in SQLite and delivers notifications when metrics exceed thresholds |
| `AlertChannel` | Defines notification delivery methods for triggered alerts |
| `AlertMetric` | Specifies telemetry metrics available for monitoring |
| `AlertSeverity` | Categorizes alert importance levels |
| `AlertConfig` | Stores configuration settings for individual alerts |
| `AlertEvent` | Records details of triggered alert instances |
| `TelemetryBackend` | Defines interface for telemetry storage systems |
| `MultiBackend` | Enables simultaneous telemetry logging across multiple storage backends |

## Related

security, validation
