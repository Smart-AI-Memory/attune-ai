---
type: faq
feature: security-audit
depth: faq
generated_at: 2026-04-14T14:39:30.436973+00:00
source_hash: 1ad7c6ac653fba529260181790342f2f2a067d4d45c694665a849d4622176019
status: generated
---

# Security Audit FAQ

## What is the security audit feature?

A comprehensive security scanning system that uses four specialized subagents (vulnerability scanner, secret detector, authentication reviewer, and remediation planner) to analyze your codebase for security issues.

## When should I use security audit?

Use security audit to scan your code for common security vulnerabilities like hardcoded secrets, path traversal risks, eval/exec usage, and injection vulnerabilities. It's particularly useful for pre-deployment security checks and regular security assessments.

## How do I run a security audit?

Create a `SecurityAuditWorkflow` instance and call its `execute()` method with your target path:

```python
from attune.workflows.security_audit import SecurityAuditWorkflow

workflow = SecurityAuditWorkflow()
result = workflow.execute(path="/path/to/your/code")
```

## What alerts can I set up for security monitoring?

You can configure alerts for various telemetry metrics using the `AlertEngine`. Set up alerts for specific security events with custom thresholds, notification channels (webhook or email), and cooldown periods.

## How do I manage alerts from the command line?

Use the `alerts()` CLI commands:
- `init()` to create new alerts interactively or with flags
- `list_cmd()` to view all configured alerts
- `delete()` to remove alerts by ID
- `enable()`/`disable()` to toggle alert states
- `watch()` to monitor telemetry in real-time

## What types of security issues does it detect?

The audit covers four main areas through specialized subagents:
- **Vulnerability scanning**: Code patterns that introduce security risks
- **Secret detection**: Hardcoded API keys, passwords, and tokens
- **Authentication review**: Auth-related security issues
- **Remediation planning**: Actionable fixes for discovered issues

## How do I debug security audit failures?

First, run the tests with `pytest -k "security" -v`. If tests pass but your audit fails, check the workflow result for subagent-specific errors. Each subagent reports findings independently, so you can isolate which component is having issues.

## Where can I find the telemetry data?

Telemetry is stored using configurable backends. Use `get_metrics()` on the AlertEngine to see current values, or `get_alert_history()` to view triggered alert events.

## Where are the source files?

- `src/attune/workflows/security_audit.py` - Main workflow orchestration
- `src/attune/security/**` - Security detection modules
- `src/attune/monitoring/**` - Alert system and telemetry

**Tags:** `security`, `audit`, `owasp`, `scanning`
