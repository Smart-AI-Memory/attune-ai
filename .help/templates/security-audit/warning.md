---
type: warning
feature: security-audit
depth: warning
generated_at: 2026-04-14T14:38:53.852392+00:00
source_hash: 1ad7c6ac653fba529260181790342f2f2a067d4d45c694665a849d4622176019
status: generated
---

# Security Audit cautions

## What to watch for

The security audit feature scans code for vulnerabilities like eval/exec usage, path traversal, hardcoded secrets, and injection risks. Several areas require careful attention to avoid false positives and security gaps.

## Risk areas

### Alert configuration drift

Misconfigured alert thresholds can flood your system with false positives or miss critical security events. The `AlertEngine.add_alert()` method accepts arbitrary threshold values without validation against realistic metric ranges.

**Mitigation:** Test alert configurations in a staging environment before production deployment. Use the `get_metrics()` method to understand baseline values before setting thresholds.

### Backend failure masking

The `MultiBackend` continues operating even when individual backends fail, potentially creating blind spots in your security monitoring. Failed backends are tracked but don't halt the audit process.

**Mitigation:** Monitor `get_failed_backends()` regularly and implement alerting when backends go offline. Use `reset_failures()` judiciously after confirming backend recovery.

### Path traversal in audit targets

The `SecurityAuditWorkflow` processes file paths without built-in validation against directory traversal attacks. Malicious audit targets could potentially access files outside the intended scope.

**Mitigation:** Validate all input paths using the provided `_validate_file_path` utility before passing them to the workflow. Never accept user-provided paths without sanitization.

### Webhook URL vulnerabilities

Alert webhooks configured through `add_alert()` accept arbitrary URLs without validation. This creates a potential for SSRF attacks or credential leakage to untrusted endpoints.

**Mitigation:** Use the `_validate_webhook_url` function to verify webhook destinations. Implement allowlisting for acceptable webhook domains in production environments.

### Secret detection gaps

The four specialized subagents (vuln-scanner, secret-detector, auth-reviewer, remediation-planner) operate independently. If one subagent fails, the others continue, potentially missing related security issues.

**Mitigation:** Monitor the `WorkflowResult` from `SecurityAuditWorkflow.execute()` for partial failures. Implement retry logic for failed subagents before accepting audit results.

## How to avoid problems

1. **Validate alert configurations.** Before deploying alerts to production, use `get_metrics()` to establish baseline values and test threshold sensitivity with `check_and_trigger()`.

2. **Monitor backend health.** Set up automated checks for `get_failed_backends()` and treat backend failures as critical issues requiring immediate attention.

3. **Sanitize audit targets.** Always validate file paths and audit scopes using the provided validation utilities before initiating security workflows.

## Source files

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`
- `src/attune/monitoring/**`

**Tags:** `security`, `audit`, `owasp`, `scanning`
