---
type: note
feature: security-audit
depth: note
generated_at: 2026-04-19T18:44:55.473918+00:00
source_hash: 7561d25b90360cf091a4fb9961180c96361f86e49fed5a0d40830d980900d622
status: generated
---

# Note: security audit

## Context

The security audit feature provides vulnerability scanning through both a workflow and monitoring system. The workflow scans code for common security issues including eval/exec usage, path traversal vulnerabilities, hardcoded secrets, and injection risks.

## Architecture

The security audit spans two main components:

**SecurityAuditWorkflow** orchestrates four specialized subagents (vuln-scanner, secret-detector, auth-reviewer, remediation-planner) to produce unified security reports. This agent-based approach allows each subagent to focus on specific vulnerability classes while maintaining comprehensive coverage.

**Alert monitoring** tracks LLM telemetry and workflow metrics through the AlertEngine, which stores configurations in SQLite and delivers notifications via multiple channels. The monitoring system supports configurable thresholds for metrics like token usage, error rates, and workflow performance.

## Key classes

- `SecurityAuditWorkflow` — The main workflow that coordinates four specialized security subagents
- `AlertEngine` — Manages alert configurations, checks thresholds, and triggers notifications
- `AlertConfig` — Dataclass defining alert rules with metrics, thresholds, and notification settings
- `AlertEvent` — Records when alerts fire, including current values and severity levels

## Integration points

The workflow and monitoring systems work together through shared telemetry. Security audits generate workflow telemetry that the alert system can monitor, enabling automated notifications when security scans detect critical issues or when the audit workflow itself experiences performance problems.

You can run security audits through the CLI (`attune workflow run security-audit`) or the Claude Code skill (`/security-audit`), with results formatted as severity-grouped findings that include CWE identifiers and clickable file links.

**Tags:** `security`, `audit`, `owasp`, `scanning`
