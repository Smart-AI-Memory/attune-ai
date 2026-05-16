---
type: error
name: security-audit-error
feature: security-audit
depth: error
generated_at: 2026-05-16T06:19:45.802002+00:00
source_hash: b5ac92e21712579189bcbb6c5f4ee162ee999a19b070da3f645661ffa7e81668
status: generated
---

# Security Audit errors

## Common error signatures

Errors in the security audit feature fall into three broad categories: workflow execution failures in `SecurityAuditWorkflow.execute()`, subagent coordination failures across the four specialized subagents (`vuln-scanner`, `secret-detector`, `auth-reviewer`, `remediation-planner`), and secrets/PII detection errors originating in the `SecretsDetector` or `PIIScrubber` classes.

Concrete signatures to watch for:

- **`ValueError`** — raised by `_validate_webhook_url` or `_validate_file_path` when an alert is misconfigured or a scan path is invalid.
- **`SecurityViolation`** — raised by the security module when a policy boundary is crossed during scanning.
- **`OSError` / `FileNotFoundError`** — raised when `SecurityAuditWorkflow.execute()` cannot access the target path passed via `--path`.
- **Alert engine errors** — `AlertEngine.check_and_trigger()` may fail silently or raise if the SQLite database at `.attune/alerts.db` is missing, locked, or corrupted.

## Where errors originate

| Source file | Relevant entry point | What goes wrong |
|---|---|---|
| `src/attune/workflows/security_audit.py` | `SecurityAuditWorkflow.execute()` | Subagent coordination failure; bad `path` argument |
| `src/attune/security/**` | `SecretsDetector`, `PIIScrubber`, `AuditLogger` | Pattern matching errors; `_validate_file_path` rejection |
| `src/attune/monitoring/alerts_cli.py` | `watch()`, `init()` | Threshold or channel misconfiguration; missing DB |
| `src/attune/monitoring/**` | `AlertEngine`, `MultiBackend` | SQLite errors; failed or degraded telemetry backends |

## How to diagnose

1. **Identify which layer failed.** A traceback rooted in `security_audit.py` points to the orchestrator or a subagent. A traceback rooted in `alerts_cli.py` or `AlertEngine` points to the monitoring layer, not the scan itself.

2. **Check the scan path.** If `execute()` raises `OSError` or `FileNotFoundError`, confirm the path you passed to `attune workflow run security-audit --path` exists and is readable. `_validate_file_path` rejects paths that resolve outside the project root.

3. **Verify alert configuration.** A `ValueError` from `_validate_webhook_url` means the webhook URL for your alert channel is malformed. Re-run `attune alerts init` and confirm the URL format for your chosen `AlertChannel`.

4. **Check the SQLite database.** `AlertEngine` stores state in `.attune/alerts.db`. If `check_and_trigger()` or `get_alert_history()` fails, check that the file exists and is not locked by another process. Delete and reinitialize if the file is corrupted.

5. **Inspect failed telemetry backends.** If `MultiBackend` is logging scan results, call `get_failed_backends()` to identify which backends have stopped accepting writes. Use `reset_failures()` to clear transient errors, or remove the degraded backend with `remove_backend()`.

6. **Check subagent output for partial failures.** `SecurityAuditWorkflow` coordinates four subagents. If the final report is missing a section (for example, no **Security** findings or no **Suggestions**), one subagent likely failed silently. Re-run with a smaller `--path` scope to isolate which domain (`vuln-scanner`, `secret-detector`, `auth-reviewer`, or `remediation-planner`) produced no output.

## Source files

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`
- `src/attune/monitoring/**`

**Tags:** `security`, `audit`, `owasp`, `scanning`, `cve`
