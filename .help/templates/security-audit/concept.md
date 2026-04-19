---
type: concept
feature: security-audit
depth: concept
generated_at: 2026-04-19T18:42:45.226514+00:00
source_hash: 7561d25b90360cf091a4fb9961180c96361f86e49fed5a0d40830d980900d622
status: generated
---

# Security Audit

A security audit scans your codebase for vulnerabilities that are easy to introduce and hard to spot in code review, using specialized subagents to detect different categories of security issues.

## Core components

The security audit system uses four specialized subagents coordinated by a workflow orchestrator:

- **`SecurityAuditWorkflow`** — Orchestrates four specialized subagents (vuln-scanner, secret-detector, auth-reviewer, remediation-planner) to produce unified security reports
- **Vulnerability detection** — Scans for code injection patterns like `eval()`, `exec()`, and `compile()` on untrusted input
- **Secret detection** — Identifies hardcoded API keys, tokens, and passwords committed to source control
- **Path validation** — Catches file operations that don't validate paths, preventing traversal attacks

## Alert and monitoring system

The audit integrates with a telemetry monitoring system that tracks security metrics over time:

- **`AlertEngine`** — Stores alert configurations in SQLite and delivers notifications when security thresholds are breached
- **`AlertChannel`** — Supports multiple notification channels (webhook, email) for different team workflows
- **`AlertMetric`** — Monitors specific security metrics like vulnerability counts or secret detection rates
- **`AlertSeverity`** — Categorizes findings from low-priority warnings to critical security issues

## Audit depth levels

You can run audits at different depths depending on your time constraints:

| Depth | Duration | Coverage |
|-------|----------|----------|
| **Quick** | ~30 seconds | Surface scan for obvious issues like `eval()` and exposed secrets |
| **Standard** | ~2 minutes | Full pattern matching with severity ratings and CWE identifiers |
| **Deep** | ~5 minutes | Multi-pass review with OWASP mapping and specific fix suggestions |

The workflow synthesizes findings into structured reports with security scores (0-100), severity-grouped vulnerabilities, and prioritized remediation steps with effort estimates.
