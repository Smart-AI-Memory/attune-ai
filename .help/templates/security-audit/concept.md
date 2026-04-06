---
feature: security-audit
depth: concept
generated_at: 2026-04-06T04:27:08.074754+00:00
source_hash: f3c7ecfc06b88ed07137562d160e3d10e0168c98f92aa060ae8fbd378b2571c4
status: generated
---

# Security Audit

## How it works

The security audit system scans code for vulnerabilities including eval/exec usage, path traversal, hardcoded secrets, and injection risks.

The main building blocks are:

- **`SecurityAuditWorkflow`** — Orchestrates four specialized security subagents to perform comprehensive code analysis.
- **`AlertEngine`** — Manages alert storage in SQLite and delivers notifications when security issues are detected.
- **`AlertChannel`** — Defines delivery methods for security alert notifications.
- **`AlertMetric`** — Tracks security-related metrics for monitoring thresholds.
- **`AlertSeverity`** — Classifies the criticality level of detected security issues.

Under the hood, this feature spans 25 source
files covering:

- SDK-native security audit workflows
- Path validation and sanitization utilities
- LLM telemetry monitoring for security events

## What connects to it

This feature relates to: security, audit, owasp, scanning.

Other parts of the codebase interact with
security audit through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `SecurityAuditWorkflow` | Orchestrates four specialized security subagents to perform comprehensive code analysis. | `src/attune/workflows/security_audit.py` |
| `AlertEngine` | Manages alert storage in SQLite and delivers notifications when security issues are detected. | `src/attune/monitoring/engine.py` |
| `AlertChannel` | Defines delivery methods for security alert notifications. | `src/attune/monitoring/models.py` |
| `AlertMetric` | Tracks security-related metrics for monitoring thresholds. | `src/attune/monitoring/models.py` |
| `AlertSeverity` | Classifies the criticality level of detected security issues. | `src/attune/monitoring/models.py` |
