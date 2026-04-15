---
type: troubleshooting
feature: security-audit
depth: troubleshooting
generated_at: 2026-04-14T14:39:10.033687+00:00
source_hash: 1ad7c6ac653fba529260181790342f2f2a067d4d45c694665a849d4622176019
status: generated
---

# Troubleshoot security audit

## Before you start

The security audit feature scans code for vulnerabilities using four specialized subagents: vulnerability scanner, secret detector, authentication reviewer, and remediation planner. It also includes an alert system for monitoring telemetry metrics.

## Symptom table

| If you observe | Check |
|----------------|-------|
| SecurityAuditWorkflow execution fails | Run `workflow.execute()` with minimal parameters and check the traceback |
| No audit findings despite known issues | Verify the audit path exists and contains the expected file types |
| Alert notifications not firing | Check `AlertEngine.get_metrics()` to confirm metric collection is working |
| Subagent timeout or hanging | Look for file I/O bottlenecks in large codebases |
| Database errors in alert system | Confirm `.attune/alerts.db` directory permissions and disk space |

## Step-by-step diagnosis

1. **Reproduce with minimal setup.**
   Create a simple test case with `SecurityAuditWorkflow()` and a small directory containing known security issues (like a hardcoded API key). If this fails, the problem is in core workflow logic.

2. **Check subagent availability.**
   The workflow relies on four subagents defined in `_SUBAGENT_NAMES`. Verify each subagent can be instantiated individually before running the full audit.

3. **Examine telemetry and alerts.**
   If alert-related issues occur:
   - Run `AlertEngine.get_metrics()` to see current metric values
   - Check `AlertEngine.get_alert_history()` for past trigger events
   - Verify alert configuration with `AlertEngine.list_alerts()`

4. **Increase logging detail.**
   Enable debug logging before calling `workflow.execute()`. The security audit uses structured logging to report findings from each subagent.

5. **Test individual components.**
   Focus on the failing component:
   - **Workflow execution**: Test `SecurityAuditWorkflow.execute()` directly
   - **Alert engine**: Use `AlertEngine.check_and_trigger()` to test threshold detection
   - **Telemetry backends**: Verify `MultiBackend.get_active_backends()` shows expected backends

## Common fixes

- **Path validation errors.** The audit expects valid file paths. Use absolute paths or ensure your working directory contains the target code.

- **Missing telemetry directory.** Create the `.attune` directory manually if alert initialization fails:
  ```bash
  mkdir -p .attune
  ```

- **SQLite permissions.** If alert database operations fail, check file permissions:
  ```bash
  chmod 644 .attune/alerts.db
  ```

- **OTEL backend unavailable.** If using OpenTelemetry export, verify the endpoint is reachable:
  ```python
  backend = OTELBackend(endpoint="your-endpoint")
  print(backend.is_available())  # Should return True
  ```

- **Alert cooldown blocking notifications.** Check if alerts are in cooldown period:
  ```python
  engine = AlertEngine()
  alerts = engine.list_alerts()
  # Look for recent trigger times vs cooldown_seconds
  ```

- **Subagent resource limits.** For large codebases, the audit may hit memory or time limits. Process smaller directory chunks or increase system resources.

## Source files

- `src/attune/workflows/security_audit.py`
- `src/attune/security/**`
- `src/attune/monitoring/**`

**Tags:** `security`, `audit`, `owasp`, `scanning`
