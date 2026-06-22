---
type: error
name: security-audit-error
feature: security-audit
depth: error
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: eae54371f777d7daaf221262e83161689f726496eaa58090e4ea0460f613d131
status: generated
---

# Security Audit errors

## Common error signatures

Failures in `SecurityAuditWorkflow` typically fall into three categories:

- **Input and path errors** — `_validate_file_path` raises when the target path is missing, outside the working directory, or not readable. You'll see this before any subagent (`vuln-scanner`, `secret-detector`, `auth-reviewer`, `remediation-planner`) starts work.
- **Secret and PII detection errors** — `SecretsDetector` and `PIIScrubber` raise `SecurityViolation` when a file cannot be read or a pattern match produces an unexpected result. `detect_secrets` can also surface these if the file path fails `_validate_file_path`.
- **Notification and webhook errors** — `_validate_webhook_url` raises when an `AlertConfig.webhook_url` is malformed. `deliver_webhook` and `deliver_email` can fail silently (returning `False`) or raise if the downstream channel is unreachable.

## How to diagnose

1. **Check whether the failure is pre-scan or mid-scan.** An error before any subagent output points to path validation (`_validate_file_path`) or workflow initialization (`SecurityAuditWorkflow.__init__`). An error after partial output points to a subagent — check which of the four names (`vuln-scanner`, `secret-detector`, `auth-reviewer`, `remediation-planner`) last appeared in the report.

2. **Inspect the `SecurityViolation` and `Severity` fields.** The `security` module exports `SecurityViolation` and `Severity` directly. If you catch a `SecurityViolation`, its severity level tells you whether the audit halted on a policy violation or logged and continued.

3. **Verify the alert engine database.** `AlertEngine` defaults to `.attune/alerts.db`. If that path is not writable, `get_alert_engine()` fails on first call. Run `attune alerts metrics` to confirm the engine can read telemetry; a failure here means the SQLite file is missing or locked.

4. **Check for failed notification backends.** After `check_and_trigger()` fires, call `MultiBackend.get_failed_backends()` to see which backends did not accept the `AlertEvent`. A non-empty list means at least one `deliver_webhook` or `deliver_email` call returned `False`.

5. **Validate webhook URLs before adding alerts.** `_validate_webhook_url` is called inside `AlertEngine.add_alert`. If `init` fails with a validation error, re-run with explicit flags (`--webhook-url`, `--email`, `--channel`) to isolate which field is rejected.

## Source files

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`
- `src/attune/monitoring/**`

**Tags:** `security`, `audit`, `owasp`, `scanning`, `cve`
