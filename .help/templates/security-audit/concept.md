---
feature: security-audit
depth: concept
generated_at: 2026-06-01T11:47:06.389393+00:00
source_hash: 6e7b17414ac506196ba40231988637e7d6eb64f9b1a8266dc41deaab14bee626
status: generated
---

# Security Audit

## How it works

Scan code for security vulnerabilities — eval/exec, path traversal, hardcoded secrets, injection risks.

The main building blocks are:

- **`SecurityAuditWorkflow`** — SDK-native security audit with four specialized subagents.
- **`AlertEngine`** — Alert engine with SQLite storage and notification delivery.
- **`AlertChannel`** — Notification channels for alerts.
- **`AlertMetric`** — Metrics that can be monitored.
- **`AlertSeverity`** — Alert severity levels.

Under the hood, this feature spans 13 source
files covering:

- Security Module for Attune AI.
- Path validation utilities for Attune AI.
- LLM Telemetry Monitoring System

## What connects to it

This feature relates to: security, audit, owasp, scanning, cve.

Other parts of the codebase interact with
security audit through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `SecurityAuditWorkflow` | SDK-native security audit with four specialized subagents. | `src/attune/workflows/security_audit.py` |
| `AlertEngine` | Alert engine with SQLite storage and notification delivery. | `src/attune/monitoring/engine.py` |
| `AlertChannel` | Notification channels for alerts. | `src/attune/monitoring/models.py` |
| `AlertMetric` | Metrics that can be monitored. | `src/attune/monitoring/models.py` |
| `AlertSeverity` | Alert severity levels. | `src/attune/monitoring/models.py` |
