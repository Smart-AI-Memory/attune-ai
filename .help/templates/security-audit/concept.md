---
type: concept
feature: security-audit
depth: concept
generated_at: 2026-04-14T14:37:46.666142+00:00
source_hash: 1ad7c6ac653fba529260181790342f2f2a067d4d45c694665a849d4622176019
status: generated
---

# Security Audit

Security audit is a comprehensive vulnerability scanner that uses four specialized AI agents to analyze codebases for security risks including hardcoded secrets, path traversal vulnerabilities, injection attacks, and authentication flaws.

## Core components

The security audit system consists of two main parts: the scanning workflow and the monitoring infrastructure.

**SecurityAuditWorkflow** orchestrates four specialized subagents (`vuln-scanner`, `secret-detector`, `auth-reviewer`, and `remediation-planner`) that each focus on specific security domains. The workflow synthesizes their findings into a unified report with an overall security score (0-100) and actionable remediation steps ordered by priority.

**AlertEngine** monitors LLM telemetry metrics and triggers notifications when security thresholds are exceeded. It stores alert configurations in SQLite and supports multiple notification channels including webhooks and email. Each alert has configurable cooldown periods and severity levels to prevent notification spam.

## Telemetry and monitoring architecture

The monitoring system captures security-related events through multiple backends:

- **MultiBackend** logs to several storage systems simultaneously, with automatic failover handling
- **OTELBackend** exports telemetry data to OpenTelemetry collectors for integration with existing observability infrastructure
- **TelemetryStore** provides structured access to historical security audit data

Alert configurations define specific metrics to watch (like vulnerability counts or secret detection rates), threshold values that trigger notifications, and delivery channels. The system tracks alert history and provides cooldown mechanisms to avoid flooding teams with duplicate notifications.

## Command-line interface

You can manage security monitoring through the `alerts` command group, which supports interactive alert creation, threshold management, and real-time monitoring. The `watch` command continuously monitors telemetry and triggers alerts, while `history` and `metrics` commands provide visibility into past events and current system state.
