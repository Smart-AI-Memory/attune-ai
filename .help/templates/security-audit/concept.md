---
feature: security-audit
depth: concept
generated_at: 2026-04-13T16:53:32.037482+00:00
source_hash: 1ad7c6ac653fba529260181790342f2f2a067d4d45c694665a849d4622176019
status: generated
---

# Security Audit

## How it works

Scans code for security vulnerabilities including eval/exec usage, path traversal risks, hardcoded secrets, and injection vulnerabilities.

The main building blocks are:

- **`SecurityAuditWorkflow`** — SDK-native security audit with four specialized subagents that analyze different vulnerability categories.
- **`AlertEngine`** — Manages alert storage in SQLite and delivers notifications when security issues are detected.
- **`AlertChannel`** — Defines delivery methods for security notifications.
- **`AlertMetric`** — Tracks security-related metrics for monitoring.
- **`AlertSeverity`** — Categorizes security findings by severity level.

Under the hood, this feature spans 13 source files covering:

- Security Module for Attune AI
- Path validation utilities for Attune AI
- LLM Telemetry Monitoring System

## What connects to it

This feature relates to: security, audit, owasp, scanning.

Other parts of the codebase interact with security audit through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `SecurityAuditWorkflow` | SDK-native security audit with four specialized subagents. | `src/attune/workflows/security_audit.py` |
| `AlertEngine` | Alert engine with SQLite storage and notification delivery. | `src/attune/monitoring/engine.py` |
| `AlertChannel` | Notification channels for alerts. | `src/attune/monitoring/models.py` |
| `AlertMetric` | Metrics that can be monitored. | `src/attune/monitoring/models.py` |
| `AlertSeverity` | Alert severity levels. | `src/attune/monitoring/models.py` |
