---
type: note
feature: security-audit
depth: note
generated_at: 2026-04-14T14:40:03.366671+00:00
source_hash: 1ad7c6ac653fba529260181790342f2f2a067d4d45c694665a849d4622176019
status: generated
---

# Note: security audit

## Context

The security audit feature scans code for vulnerabilities including eval/exec usage, path traversal risks, hardcoded secrets, and injection vulnerabilities.

## Architecture

The security audit system combines workflow orchestration with real-time monitoring. The `SecurityAuditWorkflow` coordinates four specialized subagents: vuln-scanner, secret-detector, auth-reviewer, and remediation-planner. Each subagent focuses on its domain and reports findings as structured markdown.

The workflow uses a two-stage approach. First, the subagents analyze the codebase independently. Then, the orchestrator synthesizes their findings into a unified report with an overall security score (0-100), consolidated findings organized by severity, and prioritized remediation steps with effort estimates.

## Alert monitoring

The `AlertEngine` provides real-time monitoring of LLM telemetry metrics with SQLite storage and configurable notification delivery. You can set alerts on metrics like token usage, error rates, and response times with customizable thresholds and cooldown periods.

Alerts support multiple notification channels (webhook, email) and severity levels. The engine tracks alert history and provides CLI commands for management through the `alerts()` function and related commands.

## Telemetry backends

The monitoring system supports multiple telemetry storage backends through the `TelemetryBackend` protocol. The `MultiBackend` allows simultaneous logging to multiple destinations, while `OTELBackend` exports to OpenTelemetry collectors for integration with observability platforms.

## Source files

The implementation spans three main areas:
- `src/attune/workflows/security_audit.py` — Workflow orchestration
- `src/attune/security/` — Security analysis modules
- `src/attune/monitoring/` — Alert engine and telemetry
