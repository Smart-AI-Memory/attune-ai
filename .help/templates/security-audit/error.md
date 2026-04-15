---
type: error
feature: security-audit
depth: error
generated_at: 2026-04-14T14:38:37.200384+00:00
source_hash: 1ad7c6ac653fba529260181790342f2f2a067d4d45c694665a849d4622176019
status: generated
---

# Security Audit errors

Security audit failures occur when the SecurityAuditWorkflow cannot complete its four-stage analysis (vulnerability scanning, secret detection, authentication review, and remediation planning) or when the alert monitoring system encounters configuration or telemetry issues.

## Common error signatures

- **`ValueError: Invalid metric type`** - Unknown AlertMetric passed to AlertEngine.add_alert()
- **`FileNotFoundError: Alert database not found`** - Missing SQLite database file at expected path
- **`ValidationError: Invalid webhook URL format`** - Malformed webhook URL in alert configuration
- **`ConnectionError: Failed to connect to OTEL endpoint`** - OTELBackend cannot reach OpenTelemetry collector
- **`RuntimeError: Subagent execution failed`** - One of the four security subagents (vuln-scanner, secret-detector, auth-reviewer, remediation-planner) crashed during workflow execution
- **`PermissionError: Cannot read audit target`** - Insufficient permissions to scan the specified codebase path

## Where errors originate

Security audit errors typically emerge from these components:

- **SecurityAuditWorkflow.execute()** - Core workflow orchestration failures when coordinating the four specialized subagents
- **AlertEngine methods** - Database operations, alert configuration validation, and notification delivery in the telemetry monitoring system
- **TelemetryBackend implementations** - Logging failures in MultiBackend, OTELBackend, or other telemetry storage systems
- **Alert CLI commands** - User-facing alert management operations like init(), delete(), enable(), disable()

## How to diagnose

1. **Identify the failing subagent.** If SecurityAuditWorkflow.execute() fails, check which of the four subagents (vuln-scanner, secret-detector, auth-reviewer, remediation-planner) encountered the error. The workflow logs show subagent execution order and status.

2. **Verify file permissions and paths.** Security audits require read access to the target codebase. Check that the audit path exists and is readable. For alert database errors, ensure the `.attune` directory is writable.

3. **Test alert configurations independently.** Use `AlertEngine.get_metrics()` to verify telemetry data availability before configuring alerts. Invalid metric names or unreachable webhook URLs cause alert setup failures.

4. **Check telemetry backend connectivity.** For OTELBackend errors, use `OTELBackend.is_available()` to test endpoint connectivity. Review the configured OTEL collector endpoint and network access.

5. **Validate alert thresholds.** Alert triggers depend on current telemetry values. Use the `metrics` CLI command to see current values and ensure thresholds are achievable.

## Source files

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`
- `src/attune/monitoring/**`

**Tags:** `security`, `audit`, `owasp`, `scanning`
