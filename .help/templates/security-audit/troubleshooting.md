---
type: troubleshooting
name: security-audit-troubleshooting
feature: security-audit
depth: troubleshooting
generated_at: 2026-05-16T06:19:45.810325+00:00
source_hash: b5ac92e21712579189bcbb6c5f4ee162ee999a19b070da3f645661ffa7e81668
status: generated
---

# Troubleshoot security audit

## Before you start

The security audit scans your codebase for vulnerabilities — `eval`/`exec` usage, path traversal, hardcoded secrets, and injection risks — using four specialized subagents: `vuln-scanner`, `secret-detector`, `auth-reviewer`, and `remediation-planner`. Issues can arise in the workflow orchestration, individual subagents, or the telemetry and alert systems that surround them.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Audit exits immediately with no findings | Confirm `--path` points to a directory that exists and is readable; an empty or inaccessible path returns zero findings without an error |
| `WorkflowResult` is missing one or more report sections (Summary, Security, Suggestions) | A subagent likely failed silently — check which of the four subagent names (`vuln-scanner`, `secret-detector`, `auth-reviewer`, `remediation-planner`) is absent from the raw output |
| Hardcoded secrets not detected | Verify the file extensions in your scan path are supported; `secret-detector` works on text files and may skip binary or minified files |
| Severity ratings missing or all show as `WARNING` | `AlertSeverity` defaults to `WARNING` when the severity field cannot be parsed — check that your `AlertConfig` is passing a valid `AlertSeverity` value |
| Alert never triggers even though a threshold is exceeded | The cooldown window (`cooldown_seconds`, default 3600 s) may still be active — check `get_alert_history()` for a recent trigger on the same `alert_id` |
| `check_and_trigger()` returns an empty list unexpectedly | Run `attune alerts metrics` to confirm the monitored metric has a current value; a metric with no telemetry data evaluates to zero |
| OTEL backend drops spans | `OTELBackend.is_available()` returns `False` when the endpoint is unreachable — confirm your collector URL and network access |
| `MultiBackend` silently skips a backend | Call `get_failed_backends()` to list backends that have errored; call `reset_failures()` to retry them |

## Step-by-step diagnosis

1. **Reproduce with a minimal path.**
   Run the audit against a small, known directory first:
   ```
   attune workflow run security-audit --path "src/"
   ```
   If that succeeds, the issue is likely in a specific file type or subdirectory, not the workflow itself.

2. **Check current telemetry metrics.**
   Before digging into code, confirm what the alert engine actually sees:
   ```
   attune alerts metrics
   ```
   If the metric you expect to trigger an alert shows `0.0` or is absent, the problem is upstream in telemetry collection, not in the alert threshold logic.

3. **Review alert history for the affected alert.**
   A firing alert that stops re-triggering is usually in cooldown:
   ```
   attune alerts history --alert-id <your-alert-id>
   ```
   Check the `triggered_at` timestamp on the most recent `AlertEvent`. If it is within `cooldown_seconds` of now, the alert is suppressed by design.

4. **Enable verbose logging and re-run.**
   Set the log level to `DEBUG` and re-run the workflow. The orchestrator logs subagent names and their outputs, which tells you exactly which subagent produced unexpected results.

5. **Run the related tests.**
   ```
   pytest -k "security_audit" -v
   ```
   If a test exercises the failing path, its fixtures give you a controlled starting point for narrowing down the root cause.

6. **Inspect the SQLite alerts database directly.**
   If `list_alerts()` or `get_alert()` returns unexpected results, inspect the backing store:
   ```
   sqlite3 .attune/alerts.db "SELECT * FROM alerts;"
   ```
   Corrupt or duplicate rows here explain mismatches between what you configured and what the engine evaluates.

## Common fixes

- **Audit returns no findings for a real vulnerability.** Confirm the scan depth. A quick scan (~30 s) only catches surface-level patterns like obvious `eval`/`exec` usage. For full pattern matching, use standard or deep depth:
  ```
  attune workflow run security-audit --path "src/" --depth deep
  ```

- **Alert was deleted accidentally.** Re-create it with the CLI:
  ```
  attune alerts init --metric <metric> --threshold <value> --channel <channel>
  ```
  Or non-interactively:
  ```
  attune alerts init --non-interactive --metric error_rate --threshold 0.05 --channel webhook --webhook-url https://hooks.example.com/...
  ```

- **Alert is disabled and not triggering.** Re-enable it by ID:
  ```
  attune alerts enable <alert-id>
  ```

- **OTEL backend unavailable.** `OTELBackend` requires a reachable collector endpoint. If you do not have one configured, remove the OTEL backend from your `MultiBackend` to prevent silent span loss. This change requires updating your telemetry configuration outside the security-audit feature itself.

- **MultiBackend has a failed backend.** Reset failed backends so they are retried on the next call:
  ```python
  backend.reset_failures()
  ```
  Then call `backend.flush()` to push any buffered records.

- **Stale alerts database.** If the `.attune/alerts.db` file is from a previous schema version, delete it and let `AlertEngine` recreate it:
  ```
  rm .attune/alerts.db
  ```
  All existing alert configurations will be lost; re-add them with `attune alerts init`.

## Source files

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`
- `src/attune/monitoring/**`

**Tags:** `security`, `audit`, `owasp`, `scanning`, `cve`
