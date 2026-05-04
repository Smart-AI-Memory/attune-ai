---
type: concept
feature: security-audit
depth: concept
generated_at: 2026-05-04T02:23:21.884399+00:00
source_hash: e5fdcf8a70287f5c6e2e0987e337f663cf89f93c523e4652f0c8a45e6709471e
status: generated
---

# Security Audit

A security audit scans your codebase for vulnerabilities using four specialized subagents that work together to identify different types of security risks.

## How the audit works

The `SecurityAuditWorkflow` coordinates four subagents that each focus on a specific domain:

- **vuln-scanner** — Detects code injection, SQL injection, and command injection patterns
- **secret-detector** — Finds hardcoded API keys, tokens, and passwords in source files
- **auth-reviewer** — Analyzes authentication and authorization mechanisms
- **remediation-planner** — Suggests fixes for identified vulnerabilities

Each subagent reports findings as structured markdown, which the orchestrator synthesizes into a unified security report with severity rankings (CRITICAL, HIGH, MEDIUM, LOW) and actionable remediation steps.

## Alert integration

Security audits connect to the alert system for continuous monitoring. You can configure alerts to trigger when security metrics exceed thresholds:

- **AlertEngine** — Stores alert configurations and evaluates telemetry metrics against thresholds
- **AlertConfig** — Defines what metric to monitor, the threshold value, and notification settings
- **AlertMetric** — Tracks security-related metrics like vulnerability counts or secret detection rates
- **AlertChannel** — Routes notifications to webhook URLs or email addresses when alerts fire

The alert system uses SQLite storage and includes cooldown periods to prevent notification spam.

## Output format

Security audit reports include:

| Section | Contents |
|---------|----------|
| **Summary** | Overall security score (0-100) and executive summary |
| **Security** | Findings grouped by severity with file paths and line numbers |
| **Suggestions** | Remediation steps ordered by priority with effort estimates |

This structured output makes it easy to prioritize fixes and track security improvements over time.
