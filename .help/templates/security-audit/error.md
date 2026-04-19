---
type: error
feature: security-audit
depth: error
generated_at: 2026-04-19T18:43:37.750214+00:00
source_hash: 7561d25b90360cf091a4fb9961180c96361f86e49fed5a0d40830d980900d622
status: generated
---

# Security Audit errors

Security audit failures occur during vulnerability scanning, secret detection, or alert configuration for LLM telemetry monitoring.

## Common error signatures

- **FileNotFoundError** — Path specified for audit doesn't exist or is inaccessible
- **ValidationError** — Invalid webhook URL in alert configuration
- **DatabaseError** — SQLite corruption in alert storage (`.attune/alerts.db`)
- **TypeError** — Invalid metric or channel type passed to AlertEngine
- **PermissionError** — Cannot read security audit target files
- **ConnectionError** — OTEL endpoint unreachable for telemetry export

## Where errors originate

Security audit errors typically stem from these components:

- **SecurityAuditWorkflow.execute()** — Main workflow execution with four specialized subagents (vuln-scanner, secret-detector, auth-reviewer, remediation-planner)
- **AlertEngine methods** — Alert configuration errors from `add_alert()`, `check_and_trigger()`, and database operations
- **TelemetryBackend operations** — Backend failures in `log_call()` and `log_workflow()` when recording audit runs
- **OTELBackend.flush()** — Export failures when sending telemetry to OpenTelemetry collectors
- **Path validation utilities** — File access errors during security scanning

## How to diagnose

1. **Check file paths first.** Most security audit failures are path-related. Verify the target directory exists and you have read permissions: `ls -la /path/to/scan`

2. **Examine alert database state.** If alert operations fail, check `.attune/alerts.db` exists and isn't corrupted. Run `attune alerts list` to verify basic database connectivity.

3. **Test telemetry backends individually.** For OTEL export failures, verify the endpoint with `curl -X POST $OTEL_ENDPOINT`. Check `MultiBackend.get_failed_backends()` to isolate which backend is failing.

4. **Validate webhook configurations.** Alert delivery failures often trace to malformed webhook URLs. Test the webhook endpoint directly before configuring alerts.

5. **Run with workflow debugging.** Enable verbose logging to see which of the four security subagents fails: `attune workflow run security-audit --path "src/" --verbose`

## Source files

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`
- `src/attune/monitoring/**`

**Tags:** `security`, `audit`, `owasp`, `scanning`
